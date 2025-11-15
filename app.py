from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Bot is running! Restricted Content Download Bot by @idfinderpro'

@app.route('/health')
def health_check():
    return {'status': 'healthy', 'service': 'Restricted Content Download Bot'}, 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
