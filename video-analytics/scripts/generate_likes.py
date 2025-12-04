#!/usr/bin/env python3
"""
Script to generate likes for a video.
Usage: python generate_likes.py <video_id> <count>
Example: python generate_likes.py abc-123 50
"""

import sys
import requests
import time
from typing import Optional

# Update this URL to match your Analytics service endpoint
ANALYTICS_URL = "http://localhost:8002"  # Change to your public URL when deployed

def generate_likes(video_id: str, count: int, delay: float = 0.1):
    """
    Generate likes for a video by calling the /like endpoint repeatedly.
    
    Args:
        video_id: The video ID to generate likes for
        count: Number of likes to generate
        delay: Delay between requests in seconds (default: 0.1)
    """
    endpoint = f"{ANALYTICS_URL}/like/{video_id}"
    success_count = 0
    error_count = 0
    
    print(f"Generating {count} likes for video: {video_id}")
    print(f"Endpoint: {endpoint}")
    print("-" * 50)
    
    for i in range(count):
        try:
            response = requests.post(endpoint, timeout=5)
            if response.status_code == 200:
                data = response.json()
                success_count += 1
                if (i + 1) % 10 == 0 or i == count - 1:
                    print(f"[{i + 1}/{count}] Like recorded - likes: {data.get('likes', 'N/A')}, engagement: {data.get('engagement', 'N/A')}")
            else:
                error_count += 1
                print(f"[{i + 1}/{count}] Error: HTTP {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            error_count += 1
            print(f"[{i + 1}/{count}] Request failed: {str(e)}")
        
        if delay > 0 and i < count - 1:
            time.sleep(delay)
    
    print("-" * 50)
    print(f"Completed: {success_count} successful, {error_count} errors")
    
    return success_count, error_count

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_likes.py <video_id> <count> [delay]")
        print("Example: python generate_likes.py abc-123 50 0.1")
        sys.exit(1)
    
    video_id = sys.argv[1]
    try:
        count = int(sys.argv[2])
    except ValueError:
        print("Error: count must be an integer")
        sys.exit(1)
    
    delay = float(sys.argv[3]) if len(sys.argv) > 3 else 0.1
    
    if count < 1:
        print("Error: count must be at least 1")
        sys.exit(1)
    
    success, errors = generate_likes(video_id, count, delay)
    sys.exit(0 if errors == 0 else 1)


