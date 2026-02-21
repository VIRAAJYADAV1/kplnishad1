from flask import Flask, request, jsonify, send_file, render_template
import yt_dlp
import uuid
import os
import threading

app = Flask(__name__)
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# in-memory store for download status
jobs = {}

def download_video(job_id, url, format_type, quality):
    try:
        filepath = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    percent_str = d.get('_percent_str', '0%')
                    # Clean the percent string from ANSI escape codes
                    percent_str = ''.join(c for c in percent_str if c in '0123456789.%')
                    jobs[job_id]['progress'] = float(percent_str.strip('%'))
                except Exception as e:
                    pass
            elif d['status'] == 'finished':
                jobs[job_id]['progress'] = 100
        
        ydl_opts: dict = {
            'outtmpl': filepath,
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {'youtube': ['player_client=android,web']},
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
            }
        }
        
        # Load cookies from file if it exists (for server deployments)
        if os.path.exists("cookies.txt"):
            ydl_opts['cookiefile'] = "cookies.txt"
        
        if format_type == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            if quality == '4k':
                ydl_opts['format'] = 'bestvideo[height<=2160]+bestaudio/best / best[height<=2160] / best'
            elif quality == '1080p':
                ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best / best[height<=1080] / best'
            elif quality == '720p':
                ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best / best[height<=720] / best'
            else:
                ydl_opts['format'] = 'best'
            ydl_opts['merge_output_format'] = 'mp4'
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First extract info to get title and prepare filename
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if format_type == 'audio':
                filename = filename.rsplit('.', 1)[0] + '.mp3'
            
            jobs[job_id]['ready'] = True
            jobs[job_id]['file'] = os.path.basename(filename)
            jobs[job_id]['status'] = 'finished'
            jobs[job_id]['title'] = info.get('title', 'Video')
            
    except Exception as e:
        jobs[job_id]['ready'] = False
        jobs[job_id]['error'] = str(e)
        jobs[job_id]['status'] = 'error'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def api_download():
    """ POST {url, format:"video/mp3", quality} """
    data = request.json
    url = data.get('url')
    format_type = data.get('format', 'video')
    quality = data.get('quality', '720p')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
        
    job_id = str(uuid.uuid4())
    jobs[job_id] = {'ready': False, 'progress': 0, 'status': 'downloading'}
    
    # Run the download process asynchronously
    thread = threading.Thread(target=download_video, args=(job_id, url, format_type, quality))
    thread.start()
    
    return jsonify({'id': job_id})

@app.route('/api/status/<job_id>')
def api_status(job_id):
    """ {ready:true, file:"abc.mp4"} """
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)

@app.route('/download/<filename>')
def download_file(filename):
    """ Direct download """
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
