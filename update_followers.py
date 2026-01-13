#!/usr/bin/env python3
"""Update follower counts from Facebook API."""

import json
import sqlite3
import requests

DATABASE_PATH = "data/analytics.db"

def main():
    print("Updating follower counts from Facebook API...")
    
    with open('page_tokens.json', 'r') as f:
        tokens = json.load(f)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    updated = 0
    for label, data in tokens.items():
        page_name = data.get('page_name', '')
        api_page_id = data.get('page_id', '')
        token = data.get('page_access_token', '')
        
        if not token:
            continue
        
        try:
            url = f'https://graph.facebook.com/v21.0/{api_page_id}'
            params = {'access_token': token, 'fields': 'followers_count,fan_count'}
            resp = requests.get(url, params=params)
            api_data = resp.json()
            
            followers = api_data.get('followers_count', 0)
            fans = api_data.get('fan_count', 0)
            
            cursor.execute('''
                UPDATE pages SET followers_count = ?, fan_count = ?, updated_at = datetime('now')
                WHERE LOWER(page_name) = LOWER(?)
            ''', (followers, fans, page_name))
            
            if cursor.rowcount > 0:
                updated += 1
                print(f"  {page_name}: {followers} followers")
        except Exception as e:
            print(f"  {page_name}: Error - {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\nUpdated {updated} pages")

if __name__ == "__main__":
    main()
