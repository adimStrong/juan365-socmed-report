#!/usr/bin/env python3
"""Convert short-lived Facebook tokens to long-lived tokens."""

import requests
import json
from datetime import datetime

# Facebook App credentials - Juan365
APP_ID = "2285430771870998"
APP_SECRET = "20c0ffb9eb57a8742eb1720c87172d63"

# Short-lived tokens with page names (paste new short-lived token here to convert)
SHORT_LIVED_TOKENS = {
    "Juan365": "PASTE_NEW_SHORT_LIVED_TOKEN_HERE"
}


def convert_to_long_lived_token(short_token):
    """Convert a short-lived token to a long-lived token."""
    url = "https://graph.facebook.com/v21.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": short_token
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "access_token" in data:
        return {
            "success": True,
            "access_token": data["access_token"],
            "token_type": data.get("token_type", "bearer"),
            "expires_in": data.get("expires_in", "unknown")
        }
    else:
        return {
            "success": False,
            "error": data.get("error", {}).get("message", "Unknown error")
        }


def get_page_info(access_token):
    """Get page ID and info using the access token."""
    # These are Page Access Tokens, so call /me directly to get page info
    url = "https://graph.facebook.com/v21.0/me"
    params = {
        "access_token": access_token,
        "fields": "id,name,fan_count,followers_count,about,category,link"
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "id" in data:
        return {
            "success": True,
            "page_id": data.get("id"),
            "page_name": data.get("name"),
            "page_access_token": access_token,  # The token itself is the page token
            "fan_count": data.get("fan_count"),
            "followers_count": data.get("followers_count"),
            "category": data.get("category"),
            "link": data.get("link")
        }
    else:
        return {
            "success": False,
            "error": data.get("error", {}).get("message", "Could not get page info")
        }


def main():
    print("=" * 60)
    print("Facebook Token Converter")
    print("Converting short-lived tokens to long-lived tokens")
    print("=" * 60)
    print()

    results = {}

    for page_name, short_token in SHORT_LIVED_TOKENS.items():
        print(f"\n[Processing] {page_name}")
        print("-" * 40)

        # Step 1: Convert to long-lived token
        print("  Converting token...")
        result = convert_to_long_lived_token(short_token)

        if result["success"]:
            long_token = result["access_token"]
            expires_in = result.get("expires_in", "unknown")
            if isinstance(expires_in, int):
                days = expires_in // 86400
                print(f"  [OK] Token converted! Expires in {days} days")
            else:
                print(f"  [OK] Token converted!")

            # Step 2: Get page info
            print("  Getting page info...")
            page_info = get_page_info(long_token)

            if page_info["success"]:
                print(f"  [OK] Page ID: {page_info['page_id']}")
                print(f"  [OK] Page Name: {page_info['page_name']}")
                print(f"  [OK] Fans: {page_info.get('fan_count', 'N/A')}")
                print(f"  [OK] Followers: {page_info.get('followers_count', 'N/A')}")

                results[page_name] = {
                    "user_access_token": long_token,
                    "page_id": page_info["page_id"],
                    "page_name": page_info["page_name"],
                    "page_access_token": page_info.get("page_access_token"),
                    "fan_count": page_info.get("fan_count"),
                    "followers_count": page_info.get("followers_count"),
                    "expires_in": expires_in
                }
            else:
                print(f"  [ERROR] {page_info['error']}")
                results[page_name] = {
                    "user_access_token": long_token,
                    "error": page_info["error"]
                }
        else:
            print(f"  [ERROR] {result['error']}")
            results[page_name] = {"error": result["error"]}

    # Save results to file
    print("\n" + "=" * 60)
    print("Saving results...")

    # Save to JSON for reference
    with open("page_tokens.json", "w") as f:
        json.dump(results, f, indent=2)
    print("[OK] Saved to page_tokens.json")

    # Create .env file
    env_content = f"""# Facebook App Credentials
FACEBOOK_APP_ID={APP_ID}
FACEBOOK_APP_SECRET={APP_SECRET}

# Page Access Tokens (Long-lived - ~60 days)
# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    for page_name, data in results.items():
        if "page_access_token" in data and data["page_access_token"]:
            env_key = page_name.upper().replace(" ", "_")
            env_content += f"\n# {page_name} (Page ID: {data.get('page_id', 'unknown')})\n"
            env_content += f"{env_key}_PAGE_ID={data.get('page_id', '')}\n"
            env_content += f"{env_key}_TOKEN={data.get('page_access_token', '')}\n"

    with open(".env", "w") as f:
        f.write(env_content)
    print("[OK] Saved to .env")

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    success_count = sum(1 for r in results.values() if "page_id" in r)
    print(f"Successfully converted: {success_count}/{len(SHORT_LIVED_TOKENS)} pages")

    if success_count > 0:
        print("\nPage IDs:")
        for page_name, data in results.items():
            if "page_id" in data:
                print(f"  - {page_name}: {data['page_id']}")

    print("\n[NEXT STEPS]")
    print("1. Run: python facebook_api.py to fetch page data")
    print("2. Run: python fetch_all_pages.py to populate database")


if __name__ == "__main__":
    main()
