import os
import requests

API_KEY = os.environ.get('GEMINI_API_KEY')
if not API_KEY:
    raise ValueError('Set the GEMINI_API_KEY environment variable with your API key.')

API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent'


def generate_content(prompt: str) -> dict:
    """Generate content from Gemini API using the provided prompt."""
    headers = {'Content-Type': 'application/json'}
    params = {'key': API_KEY}
    data = {
        'contents': [
            {
                'parts': [
                    {'text': prompt}
                ]
            }
        ]
    }
    response = requests.post(API_URL, headers=headers, params=params, json=data)
    response.raise_for_status()
    return response.json()


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('Usage: python gemini_client.py <prompt>')
        sys.exit(1)

    prompt = ' '.join(sys.argv[1:])
    result = generate_content(prompt)
    print(result)
