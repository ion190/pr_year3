# integration test to check that the system works as expected
import requests
import time

LEADER = 'http://localhost:8000'
FOLLOWERS = [
    'http://localhost:8001',
    'http://localhost:8002',
    'http://localhost:8003',
    'http://localhost:8004',
    'http://localhost:8005',
]

def test_basic_replication():
    key = 'integration-test-key'
    val = 'hello-123'
    r = requests.post(f'{LEADER}/put', json={'key': key, 'value': val, 'quorum': 5}, timeout=10)
    print('leader response', r.status_code, r.text)
    assert r.status_code == 200

    # small wait so followers can finish
    time.sleep(0.5)

    for f in FOLLOWERS:
        r = requests.get(f + f'/get/{key}', timeout=5)
        print(f, r.status_code, r.json())
        assert r.status_code == 200
        assert r.json()['value'] == val

if __name__ == '__main__':
    test_basic_replication()
    print('integration test passed')
