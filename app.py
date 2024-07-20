from openai import OpenAI
import base64
import json

def image_to_base64_url(image_path):
    # Open the image file in binary mode
    with open(image_path, 'rb') as image_file:
        # Read the image file and encode it to base64
        base64_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    # Get the MIME type of the image (e.g., 'image/png', 'image/jpeg')
    mime_type = f"image/{image_path.split('.')[-1]}"
    
    # Create the base64 URL
    base64_url = f"data:{mime_type};base64,{base64_string}"
    
    return base64_url

def main():
    client = OpenAI(
        api_key = "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"
    )
    img_path = "record_meal/20231030020452.jpg"

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
            "role": "system",
            "content": [
                {
                "type": "text",
                "text": """You are a helpful nutritionist who gives me helpful advice and tells me calories, fat, and protein of each meal, giving me the information using JSON.
                Example response: {"egg fried rice": {"calories": 100, "fat": 100, "protein": 100, "carbs": 100}, "soup": {"calories": 100, "fat": 100, "protein": 100, "carbs": 100}}"""
                }
            ]
            },
            {
            "role": "user",
            "content": [
                {
                "type": "image_url",
                "image_url": {
                    "url": image_to_base64_url(img_path)
                }
                }
            ]
            },
            
        ],
        temperature=1,
        max_tokens=256,
    )
   # print(response.choices[0].message.content)
    resp = json.loads(response.choices[0].message.content)
    # print(resp)
    for key, value in resp.items():
        print(f"{key} has {value['calories']} calories, {value['protein']} grams of protein, {value['fat']} grams of fat, and {value['carbs']} grams of carbs.")





if __name__ == "__main__":
    main()