#!/usr/bin/env python3
"""Facebook Graph API client for fetching page data."""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

API_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"


class FacebookAPI:
    """Facebook Graph API client."""

    def __init__(self, access_token: str):
        self.access_token = access_token

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to the Facebook Graph API."""
        if params is None:
            params = {}
        params["access_token"] = self.access_token

        url = f"{BASE_URL}/{endpoint}"
        response = requests.get(url, params=params)

        if response.status_code != 200:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "Unknown error")
            raise Exception(f"API Error: {error_msg}")

        return response.json()

    def get_page_info(self, page_id: str) -> Dict:
        """Get page information."""
        fields = "id,name,fan_count,followers_count,about,category,website,link"
        return self._make_request(page_id, {"fields": fields})

    def get_page_posts(
        self,
        page_id: str,
        limit: int = 100,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> List[Dict]:
        """Get all posts from a page with pagination."""
        fields = (
            "id,message,created_time,permalink_url,type,status_type,"
            "shares,attachments{type,media_type,title,description},"
            "reactions.summary(total_count).limit(0),"
            "comments.summary(total_count).limit(0)"
        )

        params = {"fields": fields, "limit": limit}

        if since:
            params["since"] = int(since.timestamp())
        if until:
            params["until"] = int(until.timestamp())

        all_posts = []
        endpoint = f"{page_id}/posts"

        while endpoint:
            data = self._make_request(endpoint, params)
            posts = data.get("data", [])
            all_posts.extend(posts)

            # Get next page
            paging = data.get("paging", {})
            next_url = paging.get("next")

            if next_url:
                # Extract the endpoint for next page
                endpoint = f"{page_id}/posts"
                # Get the after cursor
                cursors = paging.get("cursors", {})
                after = cursors.get("after")
                if after:
                    params["after"] = after
                else:
                    break
            else:
                break

            # Rate limiting
            time.sleep(0.5)

        return all_posts

    def get_post_reactions(self, post_id: str) -> Dict[str, int]:
        """Get detailed reaction breakdown for a post."""
        reactions = {}
        reaction_types = ["LIKE", "LOVE", "WOW", "HAHA", "SAD", "ANGRY"]

        for reaction_type in reaction_types:
            endpoint = f"{post_id}/reactions"
            params = {"type": reaction_type, "summary": "total_count", "limit": 0}

            try:
                data = self._make_request(endpoint, params)
                count = data.get("summary", {}).get("total_count", 0)
                reactions[reaction_type.lower()] = count
            except Exception:
                reactions[reaction_type.lower()] = 0

            time.sleep(0.2)  # Rate limiting

        return reactions

    def get_post_comments(self, post_id: str, page_id: str) -> Dict:
        """Get comments for a post, identifying page self-comments."""
        endpoint = f"{post_id}/comments"
        params = {
            "fields": "id,message,created_time,from{id,name}",
            "limit": 100
        }

        comments_data = self._make_request(endpoint, params)
        comments = comments_data.get("data", [])

        total_comments = len(comments)
        page_comments = 0
        user_comments = 0

        for comment in comments:
            from_user = comment.get("from", {})
            if from_user.get("id") == page_id:
                page_comments += 1
            else:
                user_comments += 1

        return {
            "total_comments": total_comments,
            "page_comments": page_comments,
            "user_comments": user_comments,
            "has_page_comment": page_comments > 0
        }

    def get_post_insights(self, post_id: str) -> Dict:
        """Get post insights (requires page token with insights permission)."""
        try:
            endpoint = f"{post_id}/insights"
            params = {
                "metric": "post_impressions,post_reach,post_engaged_users"
            }
            data = self._make_request(endpoint, params)
            insights = {}
            for item in data.get("data", []):
                insights[item["name"]] = item["values"][0]["value"]
            return insights
        except Exception as e:
            # Insights may not be available
            return {}


def classify_post_type(post: Dict) -> str:
    """Classify post type based on attachments."""
    attachments = post.get("attachments", {}).get("data", [])

    if not attachments:
        return "TEXT"

    attachment = attachments[0]
    media_type = attachment.get("media_type", "").lower()
    attach_type = attachment.get("type", "").lower()

    if media_type == "video":
        if "reel" in attach_type or "video_inline" in attach_type:
            return "REEL"
        return "VIDEO"
    elif media_type == "photo":
        return "IMAGE"
    elif media_type == "album":
        return "CAROUSEL"
    else:
        return "TEXT"


def calculate_engagement_metrics(post_data: Dict) -> Dict:
    """Calculate engagement metrics for a post."""
    reactions = post_data.get("reactions", {})
    total_reactions = sum(reactions.values())

    comments = post_data.get("comments_count", 0)
    shares = post_data.get("shares_count", 0)

    # Primary Engagement Score
    # PES = (Reactions × 1.0) + (Comments × 2.0) + (Shares × 3.0)
    pes = (total_reactions * 1.0) + (comments * 2.0) + (shares * 3.0)

    # Quality Engagement Score
    # QES = (Love + Wow + Haha) / Total Reactions × 100
    love = reactions.get("love", 0)
    wow = reactions.get("wow", 0)
    haha = reactions.get("haha", 0)
    qes = ((love + wow + haha) / total_reactions * 100) if total_reactions > 0 else 0

    # Viral Coefficient
    total_engagement = total_reactions + comments + shares
    viral_coefficient = (shares / total_engagement) if total_engagement > 0 else 0

    return {
        "total_reactions": total_reactions,
        "total_engagement": total_engagement,
        "pes": round(pes, 2),
        "qes": round(qes, 2),
        "viral_coefficient": round(viral_coefficient, 4)
    }


def fetch_page_data(page_access_token: str, page_id: str, days_back: int = 90) -> Dict:
    """Fetch comprehensive data for a page."""
    api = FacebookAPI(page_access_token)

    # Get page info
    print(f"  Fetching page info...")
    page_info = api.get_page_info(page_id)

    # Get posts
    since_date = datetime.now() - timedelta(days=days_back)
    print(f"  Fetching posts (last {days_back} days)...")
    posts = api.get_page_posts(page_id, since=since_date)
    print(f"  Found {len(posts)} posts")

    # Process each post
    processed_posts = []
    for i, post in enumerate(posts):
        post_id = post["id"]
        print(f"  Processing post {i+1}/{len(posts)}...", end="\r")

        # Get detailed reactions
        reactions = api.get_post_reactions(post_id)

        # Get comments analysis
        comments_analysis = api.get_post_comments(post_id, page_id)

        # Get shares
        shares_count = post.get("shares", {}).get("count", 0)

        # Classify post type
        post_type = classify_post_type(post)

        # Build post data
        post_data = {
            "post_id": post_id,
            "message": post.get("message", "")[:500],  # Truncate long messages
            "created_time": post.get("created_time"),
            "permalink": post.get("permalink_url"),
            "post_type": post_type,
            "reactions": reactions,
            "reactions_total": post.get("reactions", {}).get("summary", {}).get("total_count", 0),
            "comments_count": post.get("comments", {}).get("summary", {}).get("total_count", 0),
            "shares_count": shares_count,
            "page_comments": comments_analysis.get("page_comments", 0),
            "has_page_comment": comments_analysis.get("has_page_comment", False)
        }

        # Calculate engagement metrics
        post_data["metrics"] = calculate_engagement_metrics({
            "reactions": reactions,
            "comments_count": post_data["comments_count"],
            "shares_count": shares_count
        })

        processed_posts.append(post_data)

        # Rate limiting
        time.sleep(0.3)

    print()  # New line after progress

    return {
        "page_info": page_info,
        "posts": processed_posts,
        "fetch_date": datetime.now().isoformat()
    }


if __name__ == "__main__":
    # Test with a token (for debugging)
    print("Facebook API module loaded.")
    print("Use fetch_page_data(token, page_id) to fetch data.")
