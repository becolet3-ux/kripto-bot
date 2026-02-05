import tweepy
import praw
from textblob import TextBlob
from collections import Counter
import re
from typing import Dict, Optional
from src.utils.logger import log

class SentimentAnalyzer:
    """Twitter ve Reddit'ten sentiment analizi"""
    
    def __init__(self, twitter_api_key: Optional[str] = None, reddit_credentials: Optional[Dict] = None):
        self.mock_mode = False
        
        # Twitter API
        if twitter_api_key:
            try:
                self.twitter_client = tweepy.Client(bearer_token=twitter_api_key)
            except Exception as e:
                log(f"⚠️ Twitter Auth Failed: {e}. Switching to Mock Mode for Twitter.")
                self.twitter_client = None
        else:
            self.twitter_client = None
        
        # Reddit API
        if reddit_credentials and 'client_id' in reddit_credentials:
            try:
                self.reddit = praw.Reddit(
                    client_id=reddit_credentials['client_id'],
                    client_secret=reddit_credentials['client_secret'],
                    user_agent=reddit_credentials['user_agent']
                )
            except Exception as e:
                log(f"⚠️ Reddit Auth Failed: {e}. Switching to Mock Mode for Reddit.")
                self.reddit = None
        else:
            self.reddit = None
            
        if not self.twitter_client and not self.reddit:
            self.mock_mode = True
            log("ℹ️ Sentiment Analyzer initialized in MOCK MODE (No API keys provided).")

    def analyze_twitter_sentiment(self, symbol: str, count: int = 100) -> Dict:
        """Twitter'dan sentiment analizi"""
        if not self.twitter_client:
            return {
                'platform': 'Twitter',
                'symbol': symbol,
                'tweet_count': 0,
                'avg_sentiment': 0,
                'sentiment_score': 5.0, # Neutral
                'confidence': 0.0,
                'note': 'Mock Data'
            }
        
        # Hashtag'leri oluştur
        search_terms = [
            f"${symbol}",
            f"#{symbol}",
            f"{symbol.replace('USDT', '')} crypto"
        ]
        
        tweets = []
        for term in search_terms:
            try:
                response = self.twitter_client.search_recent_tweets(
                    query=term,
                    max_results=count,
                    tweet_fields=['created_at', 'public_metrics']
                )
                
                if response.data:
                    tweets.extend(response.data)
            except Exception as e:
                log(f"Twitter API error for {term}: {e}")
        
        if not tweets:
             return {
                'platform': 'Twitter',
                'symbol': symbol,
                'tweet_count': 0,
                'avg_sentiment': 0,
                'sentiment_score': 5.0,
                'confidence': 0.0
            }

        # Sentiment analizi
        sentiments = []
        for tweet in tweets:
            analysis = TextBlob(tweet.text)
            sentiments.append({
                'polarity': analysis.sentiment.polarity,  # -1 to 1
                'subjectivity': analysis.sentiment.subjectivity,  # 0 to 1
                'engagement': tweet.public_metrics['like_count'] + tweet.public_metrics['retweet_count']
            })
        
        # Ağırlıklı ortalama (engagement'a göre)
        total_engagement = sum(s['engagement'] for s in sentiments)
        weighted_sentiment = sum(
            s['polarity'] * (s['engagement'] / total_engagement) 
            for s in sentiments
        ) if total_engagement > 0 else 0
        
        return {
            'platform': 'Twitter',
            'symbol': symbol,
            'tweet_count': len(tweets),
            'avg_sentiment': weighted_sentiment,
            'sentiment_score': self._convert_to_score(weighted_sentiment),
            'confidence': min(len(tweets) / count, 1.0)
        }
    
    def analyze_reddit_sentiment(self, symbol: str, subreddit: str = 'CryptoCurrency') -> Dict:
        """Reddit'ten sentiment analizi"""
        if not self.reddit:
            return {
                'platform': 'Reddit', 
                'symbol': symbol, 
                'sentiment_score': 5.0, # Neutral
                'confidence': 0.0,
                'note': 'Mock Data'
            }
        
        coin_name = symbol.replace('USDT', '').replace('BTC', '')
        
        sentiments = []
        try:
            # Subreddit'ten veri çek
            submissions = self.reddit.subreddit(subreddit).search(
                coin_name,
                limit=50,
                sort='hot'
            )
            
            for submission in submissions:
                # Başlık analizi
                title_sentiment = TextBlob(submission.title).sentiment.polarity
                
                # Comment'ler
                submission.comments.replace_more(limit=0)
                for comment in submission.comments.list()[:10]:
                    comment_sentiment = TextBlob(comment.body).sentiment.polarity
                    sentiments.append({
                        'polarity': comment_sentiment,
                        'score': comment.score
                    })
        except Exception as e:
            log(f"Reddit API error: {e}")
        
        if not sentiments:
            return {'platform': 'Reddit', 'symbol': symbol, 'sentiment_score': 5.0, 'confidence': 0.0}
        
        # Upvote ağırlıklı ortalama
        total_score = sum(s['score'] for s in sentiments)
        weighted_sentiment = sum(
            s['polarity'] * (s['score'] / total_score)
            for s in sentiments
        ) if total_score > 0 else 0
        
        return {
            'platform': 'Reddit',
            'symbol': symbol,
            'post_count': len(sentiments),
            'avg_sentiment': weighted_sentiment,
            'sentiment_score': self._convert_to_score(weighted_sentiment),
            'confidence': min(len(sentiments) / 50, 1.0)
        }
    
    def get_combined_sentiment(self, symbol: str) -> Dict:
        """Tüm platformlardan birleşik sentiment"""
        
        twitter_sentiment = self.analyze_twitter_sentiment(symbol)
        reddit_sentiment = self.analyze_reddit_sentiment(symbol)
        
        # Güven skoruna göre ağırlıklandır
        twitter_weight = twitter_sentiment['confidence']
        reddit_weight = reddit_sentiment['confidence']
        total_weight = twitter_weight + reddit_weight
        
        if total_weight == 0:
            return {'sentiment_score': 5.0, 'signal': 'NEUTRAL'}
        
        combined_score = (
            twitter_sentiment['sentiment_score'] * twitter_weight +
            reddit_sentiment['sentiment_score'] * reddit_weight
        ) / total_weight
        
        return {
            'symbol': symbol,
            'combined_score': combined_score,
            'twitter': twitter_sentiment,
            'reddit': reddit_sentiment,
            'signal': self._get_signal(combined_score)
        }
    
    def _convert_to_score(self, polarity: float) -> float:
        """Polarity (-1 to 1) -> Score (0 to 10)"""
        return (polarity + 1) * 5
    
    def _get_signal(self, score: float) -> str:
        """Sentiment skoruna göre sinyal"""
        if score >= 7:
            return 'BULLISH'
        elif score >= 5.5:
            return 'SLIGHTLY_BULLISH'
        elif score >= 4.5:
            return 'NEUTRAL'
        elif score >= 3:
            return 'SLIGHTLY_BEARISH'
        else:
            return 'BEARISH'
