let currentInterval = null;

async function startDownload() {
    const url = document.getElementById('urlInput').value.trim();
    const format = document.getElementById('formatSelect').value;
    const quality = document.getElementById('qualitySelect').value;

    if (!url) {
        alert("Please enter a YouTube URL");
        return;
    }

    // UI Updates
    document.getElementById('downloadBtn').disabled = true;
    document.getElementById('statusContainer').classList.remove('hidden');
    document.getElementById('resultContainer').classList.add('hidden');
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('statusText').innerText = 'Initializing Download...';

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, format, quality })
        });

        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }

        const jobId = data.id;
        checkStatus(jobId);

    } catch (error) {
        document.getElementById('statusText').innerText = "Error: " + error.message;
        document.getElementById('downloadBtn').disabled = false;
        document.getElementById('statusText').style.color = "#ff4444";
    }
}

function checkStatus(jobId) {
    if (currentInterval) clearInterval(currentInterval);
    
    currentInterval = setInterval(async () => {
        try {
            const res = await fetch(`/api/status/${jobId}`);
            if (!res.ok) throw new Error("Status check failed");
            const data = await res.json();

            if (data.error) {
                clearInterval(currentInterval);
                document.getElementById('statusText').innerText = "Error: " + data.error;
                document.getElementById('statusText').style.color = "#ff4444";
                document.getElementById('downloadBtn').disabled = false;
                return;
            }

            if (data.progress !== undefined) {
                document.getElementById('progressBar').style.width = `${data.progress}%`;
                document.getElementById('statusText').innerText = `Downloading... ${Math.round(data.progress)}%`;
            }

            if (data.ready) {
                clearInterval(currentInterval);
                document.getElementById('statusText').innerText = "File Ready for Download!";
                document.getElementById('progressBar').style.width = '100%';
                
                const resultDiv = document.getElementById('resultContainer');
                const downloadLink = document.getElementById('downloadLink');
                
                // Point directly to the server download route
                downloadLink.href = `/download/${encodeURIComponent(data.file)}`;
                
                resultDiv.classList.remove('hidden');
                document.getElementById('downloadBtn').disabled = false;
            }

            if (data.status === 'error') {
                clearInterval(currentInterval);
                document.getElementById('statusText').innerText = "Failed: " + data.error;
                document.getElementById('statusText').style.color = "#ff4444";
                document.getElementById('downloadBtn').disabled = false;
            }
        } catch (e) {
            console.error("Status check error:", e);
        }
    }, 1500); // Check every 1.5 seconds
}
