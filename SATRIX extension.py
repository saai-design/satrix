import os
import base64
import numpy as np
import cv2
from flask import Flask, jsonify, render_template_string
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['UPLOAD_FOLDER'] = 'uploads'
socketio = SocketIO(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Process the captured image stored on disk
def process_image(image_path):
    img = cv2.imread(image_path)
    
    # Perform analysis on the image (simplified for this example)
    analysis_results = {
        "chlorophyll_content": "75%", 
        "damage_level": "20%", 
        "pest_invasion_level": "5%", 
        "fertilizer_suggestion": "Use NPK 20-20-20",
        "thermal_image": base64.b64encode(img).decode('utf-8'),
        "input_image": base64.b64encode(img).decode('utf-8')
    }
    return analysis_results

# Serve the page with video stream
@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Satrix the Saviour</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #2ecc71; /* Green background */
            text-align: center;
            padding: 20px;
        }

        .container {
            max-width: 800px;
            margin: auto;
            background-color: #fff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
        }

        h1 {
            color: #2c3e50;
        }

        button {
            background-color: #3498db;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }

        button:hover {
            background-color: #2980b9;
        }

        #result {
            margin-top: 20px;
        }

        #video-container {
            margin-bottom: 20px;
        }

        #thermalImage, #inputImage {
            max-width: 500px;
        }

        video {
            border: 2px solid #ccc;
            border-radius: 8px;
        }

        .message {
            font-size: 18px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Satrix the Saviour</h1>

        <!-- Live video stream section -->
        <div id="video-container">
            <h3>Start Live Video Stream</h3>
            <button onclick="startLiveStream()">Start Stream</button>
            <button onclick="stopLiveStream()" id="stopButton" disabled>Stop Stream</button>
            <button onclick="captureImage()" id="captureButton" disabled>Capture Image</button>
            <video id="video" width="640" height="480" autoplay></video>
        </div>

        <!-- Displaying results -->
        <div id="result">
            <h3>Analysis Results:</h3>
            <p>Chlorophyll Content: <span id="chlorophyll">0%</span></p>
            <p>Damage Level: <span id="damageLevel">0%</span></p>
            <p>Pest Invasion Level: <span id="pestLevel">0%</span></p>
            <p>Fertilizer Suggestion: <span id="fertilizer">N/A</span></p>
            <h4>Thermal Image of Damage:</h4>
            <img id="thermalImage" src="" alt="Thermal Image">
            <h4>Original Input Image:</h4>
            <img id="inputImage" src="" alt="Input Image">
        </div>

        <div id="liveStreamMessage" class="message"></div>
    </div>

    <script src="https://cdn.socket.io/4.4.1/socket.io.min.js"></script>
    <script>
        const socket = io.connect('http://' + document.domain + ':' + location.port);
        let videoStream = null;
        let frameInterval = null;

        // Start video stream and capture frames
        function startLiveStream() {
            const videoElement = document.getElementById('video');
            const messageElement = document.getElementById('liveStreamMessage');
            messageElement.innerText = "Live stream is active. Processing frames...";

            navigator.mediaDevices.getUserMedia({ video: true })
                .then(stream => {
                    videoElement.srcObject = stream;
                    videoStream = stream;

                    // Capture frames every 100ms and send to the server
                    frameInterval = setInterval(() => {
                        const canvas = document.createElement('canvas');
                        canvas.width = videoElement.videoWidth;
                        canvas.height = videoElement.videoHeight;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
                        const frameData = canvas.toDataURL('image/png');
                        socket.emit('send_frame', frameData);
                    }, 100); // Send frame every 100ms

                    // Disable start button and enable stop button
                    document.querySelector('button[onclick="startLiveStream()"]').disabled = true;
                    document.getElementById('stopButton').disabled = false;
                    document.getElementById('captureButton').disabled = false;
                })
                .catch(error => {
                    console.error("Error accessing webcam:", error);
                    messageElement.innerText = "Error accessing webcam.";
                });
        }

        // Stop video stream
        function stopLiveStream() {
            if (videoStream) {
                videoStream.getTracks().forEach(track => track.stop());
            }
            if (frameInterval) {
                clearInterval(frameInterval);
            }

            const videoElement = document.getElementById('video');
            videoElement.srcObject = null;
            videoStream = null;

            const messageElement = document.getElementById('liveStreamMessage');
            messageElement.innerText = "Live stream stopped.";

            // Disable stop button and enable start button
            document.querySelector('button[onclick="startLiveStream()"]').disabled = false;
            document.getElementById('stopButton').disabled = true;
            document.getElementById('captureButton').disabled = true;
        }

        // Capture image from live stream
        function captureImage() {
            const videoElement = document.getElementById('video');
            const canvas = document.createElement('canvas');
            canvas.width = videoElement.videoWidth;
            canvas.height = videoElement.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
            const imageData = canvas.toDataURL('image/png');
            
            // Send captured image to the backend for processing and saving to disk
            socket.emit('capture_image', imageData);
        }

        // Listen for analysis result from captured image
        socket.on('analysis_result', (data) => {
            updateResults(data);
        });

        // Update the result display
        function updateResults(data) {
            document.getElementById('chlorophyll').innerText = data.chlorophyll_content;
            document.getElementById('damageLevel').innerText = data.damage_level;
            document.getElementById('pestLevel').innerText = data.pest_invasion_level;
            document.getElementById('fertilizer').innerText = data.fertilizer_suggestion;
            document.getElementById('thermalImage').src = 'data:image/png;base64,' + data.thermal_image;
            document.getElementById('inputImage').src = 'data:image/png;base64,' + data.input_image;
        }
    </script>
</body>
</html>
""")

# Handle the captured image from the frontend
@socketio.on('capture_image')
def handle_captured_image(image_data):
    # Save the captured image to disk
    image_data = image_data.split(',')[1]  # Remove the prefix 'data:image/png;base64,'
    image_bytes = base64.b64decode(image_data)
    
    # Generate a secure filename and save the image to disk
    filename = secure_filename("captured_image.png")
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with open(file_path, 'wb') as f:
        f.write(image_bytes)
    
    # Process the saved image and get analysis results
    analysis_results = process_image(file_path)
    
    # Emit the analysis results back to the frontend
    emit('analysis_result', analysis_results)

if __name__ == '__main__':
    socketio.run(app, debug=True)
