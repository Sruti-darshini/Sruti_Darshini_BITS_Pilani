"""
Test script for the /extract-bill-data endpoint
"""
import requests
import json

# Test URL from the Postman collection
test_url = "https://hackrx.blob.core.windows.net/assets/datathon-IIT/sample_2.png?sv=2025-07-05&spr=https&st=2025-11-24T14%3A13%3A22Z&se=2026-11-25T14%3A13%3A00Z&sr=b&sp=r&sig=WFJYfNw0PJdZOpOYlsoAW0XujYGG1x2HSbcDREiFXSU%3D"

# API endpoint
api_url = "http://localhost:8000/extract-bill-data"

# Request payload
payload = {
    "document": test_url
}

print("Testing /extract-bill-data endpoint...")
print(f"Document URL: {test_url[:80]}...")
print()

try:
    # Make request
    response = requests.post(api_url, json=payload, timeout=120)
    
    print(f"Status Code: {response.status_code}")
    print()
    
    # Parse response
    result = response.json()
    
    # Pretty print response
    print("Response:")
    print(json.dumps(result, indent=2))
    print()
    
    # Validate response structure
    print("Validation:")
    print(f"✓ is_success: {result.get('is_success')}")
    
    if result.get('is_success'):
        # Check required fields
        has_token_usage = 'token_usage' in result
        has_data = 'data' in result
        
        print(f"✓ has token_usage: {has_token_usage}")
        print(f"✓ has data: {has_data}")
        
        if has_token_usage:
            token_usage = result['token_usage']
            print(f"  - total_tokens: {token_usage.get('total_tokens')}")
            print(f"  - input_tokens: {token_usage.get('input_tokens')}")
            print(f"  - output_tokens: {token_usage.get('output_tokens')}")
        
        if has_data:
            data = result['data']
            print(f"✓ total_item_count: {data.get('total_item_count')}")
            
            # Check pagewise_line_items
            if 'pagewise_line_items' in data:
                for page in data['pagewise_line_items']:
                    print(f"  - Page {page.get('page_no')}: {page.get('page_type')} with {len(page.get('bill_items', []))} items")
                    
                    # Show first item as example
                    if page.get('bill_items'):
                        item = page['bill_items'][0]
                        print(f"    Example item: {item.get('item_name')}")
                        print(f"      - quantity: {item.get('item_quantity')}")
                        print(f"      - rate: {item.get('item_rate')}")
                        print(f"      - amount: {item.get('item_amount')}")
    else:
        print(f"✗ Error: {result.get('message')}")
    
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
except Exception as e:
    print(f"Error: {e}")
