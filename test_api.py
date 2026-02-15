import http.client, json, time

def test_api():
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 5000)
        
        # Subscribe
        conn.request("POST", "/api/subscribe")
        resp = conn.getresponse()
        data = resp.read().decode()
        print(f"Subscribe response: {resp.status} {data}")
        
        cookies = resp.getheader('Set-Cookie')
        headers = {'Content-type': 'application/json'}
        if cookies:
            headers['Cookie'] = cookies

        # Generate
        print("Generating idea...")
        body = json.dumps({'businessType': 'test_business', 'mood': 'fun', 'goal': 'sales'})
        conn.request("POST", "/api/generate", body, headers)
        resp = conn.getresponse()
        data = resp.read().decode()
        print(f"Generate response: {resp.status} {data}")
        
        conn.close()
    except Exception as e:
        print(f"Test script error: {e}")

if __name__ == "__main__":
    time.sleep(2) # wait for server to settle
    test_api()
