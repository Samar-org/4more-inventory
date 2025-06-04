"""
Product Scraper & Inventory Management System for Airtable

IMPORTANT: INSPECTION PHOTOS NOT SAVING?
========================================
The most common issue is that the field name in Airtable doesn't match.

1. Check your Airtable base for the EXACT field name for inspection photos
2. Update line ~1750 in this file: INSPECTION_PHOTOS_FIELD_NAME = "Your Field Name"
3. Common variations:
   - "Inspection Photos" (default)
   - "InspectionPhotos" (no space)
   - "Inspection_Photos" (underscore)
   - "Photos"
   - "Attachments"
   - "Inspection Images"

The field must be of type "Attachment" in Airtable.

QUICK SETUP GUIDE:

1. Install Requirements:
   pip install flask requests beautifulsoup4 python-dotenv cloudinary

2. Create a .env file with:
   # Airtable (Required)
   AIRTABLE_API_KEY=your_api_key
   AIRTABLE_BASE_ID=your_base_id
   AIRTABLE_TABLE_NAME=Items
   
   # Cloudinary (For photo uploads - FREE account)
   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=your_api_key
   CLOUDINARY_API_SECRET=your_api_secret

3. Get FREE Cloudinary account:
   - Go to https://cloudinary.com/users/register/free
   - Sign up (no credit card required)
   - Find credentials in Dashboard → Account Details
   - Free tier includes 25GB storage + 25GB bandwidth/month

4. Update field names in submit() function to match your Airtable

5. Run: python process-item.py
"""

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template_string, request, jsonify
import re
from urllib.parse import urljoin, urlparse
import json
import os
from dotenv import load_dotenv
from datetime import datetime
import time
import random

# Optional: Import Cloudinary for photo uploads
try:
    import cloudinary
    import cloudinary.uploader
    CLOUDINARY_AVAILABLE = True
except ImportError:
    CLOUDINARY_AVAILABLE = False
    print("Cloudinary not installed. Run: pip install cloudinary")

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration from environment variables
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID')
# Default to 'Items' if not specified
AIRTABLE_TABLE_NAME = os.getenv('AIRTABLE_TABLE_NAME', 'Items')

# Cloudinary configuration (optional, for photo uploads)
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')

# Configure Cloudinary if credentials are available
if CLOUDINARY_AVAILABLE and CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET
    )
    print("✓ Cloudinary configured for photo uploads")
else:
    print("⚠ Cloudinary not configured. Inspection photos will not be uploaded.")
    print("  To enable: 1) pip install cloudinary")
    print("  2) Add CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET to .env")

# Validate that required environment variables are set
if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
    print("\n" + "="*60)
    print("⚠️  AIRTABLE SETUP REQUIRED")
    print("="*60)
    print("1. Create a .env file in the same directory as this script")
    print("2. Add these lines:")
    print("   AIRTABLE_API_KEY=your_api_key")
    print("   AIRTABLE_BASE_ID=your_base_id")
    print("   AIRTABLE_TABLE_NAME=Items")
    print("\n📸 For inspection photo uploads, also add:")
    print("   CLOUDINARY_CLOUD_NAME=your_cloud_name")
    print("   CLOUDINARY_API_KEY=your_cloudinary_key")
    print("   CLOUDINARY_API_SECRET=your_cloudinary_secret")
    print("\n🔗 Get Cloudinary credentials (free) at: https://cloudinary.com")
    print("="*60 + "\n")

# Replace your entire HTML_TEMPLATE with this clean version

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>4more Inventory System</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html5-qrcode/2.3.8/html5-qrcode.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary-red: #DC143C;
            --primary-green: #2ECC40;
            --primary-yellow: #FFDC00;
            --primary-blue: #0074D9;
            --dark: #111111;
            --light-gray: #f8f9fa;
            --border-gray: #e0e0e0;
            --text-gray: #6c757d;
            --success: #28a745;
            --danger: #dc3545;
            --warning: #ffc107;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #ffffff;
            color: var(--dark);
            line-height: 1.6;
            font-size: 14px;
        }

        .header {
            background: #ffffff;
            border-bottom: 1px solid var(--border-gray);
            padding: 20px 0;
            margin-bottom: 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        .logo-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .logo {
            display: flex;
            align-items: center;
            font-size: 36px;
            font-weight: 900;
            text-decoration: none;
            color: var(--dark);
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }

        .card {
            background: white;
            border: 1px solid var(--border-gray);
            border-radius: 8px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 6px;
            font-weight: 500;
            color: var(--dark);
            font-size: 13px;
        }

        input[type="text"],
        input[type="url"],
        input[type="number"],
        select,
        textarea {
            width: 100%;
            padding: 10px 14px;
            border: 1px solid var(--border-gray);
            border-radius: 6px;
            font-size: 14px;
            transition: all 0.2s;
            background-color: #ffffff;
        }

        textarea {
            resize: vertical;
            min-height: 80px;
        }

        .input-group {
            display: flex;
            gap: 10px;
            align-items: stretch;
        }

        .input-group input {
            flex: 1;
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }

        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .btn-success {
            background-color: var(--primary-green);
            color: white;
        }

        .btn-success:hover {
            background-color: #27ae60;
        }

        .btn-danger {
            background-color: var(--primary-red);
            color: white;
        }

        .btn-outline {
            background-color: transparent;
            border: 1px solid var(--border-gray);
            color: var(--dark);
        }

        .btn-scan {
            background-color: var(--primary-blue);
            color: white;
            padding: 8px 16px;
            font-size: 13px;
        }

        .btn-scan:hover {
            background-color: #0059a5;
        }

        .message {
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 20px;
            display: none;
            font-size: 14px;
        }

        .message-success {
            background-color: rgba(46, 204, 64, 0.1);
            color: var(--success);
            border: 1px solid rgba(46, 204, 64, 0.2);
        }

        .message-error {
            background-color: rgba(220, 20, 60, 0.1);
            color: var(--danger);
            border: 1px solid rgba(220, 20, 60, 0.2);
        }

        .message-info {
            background-color: rgba(0, 116, 217, 0.1);
            color: var(--primary-blue);
            border: 1px solid rgba(0, 116, 217, 0.2);
        }

        .message-warning {
            background-color: rgba(255, 193, 7, 0.1);
            color: var(--warning);
            border: 1px solid rgba(255, 193, 7, 0.2);
        }

        .scraped-info {
            background-color: var(--light-gray);
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }

        .scraped-images {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 12px;
            margin-top: 15px;
        }

        .image-container {
            position: relative;
            border-radius: 6px;
            overflow: hidden;
            background: white;
            border: 1px solid var(--border-gray);
            transition: all 0.2s;
        }

        .scraped-images img {
            width: 100%;
            height: 120px;
            object-fit: cover;
            cursor: pointer;
        }

        .scraped-images input[type="checkbox"] {
            position: absolute;
            top: 8px;
            left: 8px;
            width: 20px;
            height: 20px;
            cursor: pointer;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }

        @media (max-width: 768px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
        }

        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(0,0,0,0.1);
            border-radius: 50%;
            border-top-color: var(--primary-blue);
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }

        .modal-content {
            background-color: white;
            margin: 5% auto;
            padding: 30px;
            border-radius: 12px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            position: relative;
        }

        .close {
            color: var(--text-gray);
            font-size: 28px;
            font-weight: 300;
            cursor: pointer;
            line-height: 1;
            position: absolute;
            right: 20px;
            top: 20px;
        }

        .close:hover {
            color: var(--dark);
        }

        #reader {
            width: 100%;
            margin: 20px 0;
        }

        .debug-info {
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            padding: 10px;
            margin-top: 10px;
            font-family: monospace;
            font-size: 12px;
            border-radius: 4px;
            max-height: 200px;
            overflow-y: auto;
        }

        .scan-icon {
            display: inline-block;
            width: 16px;
            height: 16px;
            margin-right: 4px;
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="logo-container">
            <div class="logo">
                <span style="color: var(--primary-red); font-size: 48px;">4</span>
                <span>more</span>
            </div>
            <div>Inventory Management System</div>
        </div>
    </header>

    <div class="container">
        <div class="message message-success" id="successMessage"></div>
        <div class="message message-error" id="errorMessage"></div>
        <div class="message message-warning" id="warningMessage"></div>
        <div class="message message-info" id="loadingMessage">
            <span class="spinner"></span> Scraping product information...
        </div>

        <form id="inventoryForm">
            <div class="card">
                <h2>Product Information</h2>
                <p>Enter a product URL to automatically fetch details</p>
                
                <div class="form-group">
                    <label for="url">Product URL</label>
                    <div class="input-group">
                        <input type="url" id="url" name="url" placeholder="https://example.com/product" required>
                        <button type="button" class="btn btn-success" id="scrapeBtn">
                            Scrape Info
                        </button>
                    </div>
                </div>

                <div class="scraped-info" id="scrapedInfo">
                    <h3>Scraped Product Information</h3>
                    <div id="scrapedDetails"></div>
                    <div id="debugInfo" class="debug-info" style="display: none;"></div>
                </div>
            </div>

            <div class="card">
                <h2>Basic Information</h2>
                
                <div class="grid-2">
                    <div class="form-group">
                        <label for="store">4more Store *</label>
                        <select id="store" name="store" required>
                            <option value="Bid4more">Bid4more</option>
                            <option value="Store2">Store 2</option>
                            <option value="Store3">Store 3</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="sku">SKU *</label>
                        <div class="input-group">
                            <input type="text" id="sku" name="sku" required>
                            <button type="button" class="btn btn-scan" onclick="openScanner('sku')">
                                <svg class="scan-icon" fill="white" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M3 11h2V3H3v8zm0 10h2v-8H3v8zM5 3v2h14V3H5zm14 18v-2H5v2h14zM21 3h-2v8h2V3zm0 10h-2v8h2v-8zM11 7h2v10h-2V7zm-2 2H7v6h2V9zm6 0h2v6h-2V9z"/>
                                </svg>
                                Scan
                            </button>
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="gtin">GTIN (Barcode)</label>
                        <input type="text" id="gtin" name="gtin" placeholder="UPC/EAN/ISBN">
                    </div>

                    <div class="form-group">
                        <label for="shelfCode">Shelf Location</label>
                        <div class="input-group">
                            <input type="text" id="shelfCode" name="shelfCode">
                            <button type="button" class="btn btn-scan" onclick="openScanner('shelfCode')">
                                <svg class="scan-icon" fill="white" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M3 11h2V3H3v8zm0 10h2v-8H3v8zM5 3v2h14V3H5zm14 18v-2H5v2h14zM21 3h-2v8h2V3zm0 10h-2v8h2v-8zM11 7h2v10h-2V7zm-2 2H7v6h2V9zm6 0h2v6h-2V9z"/>
                                </svg>
                                Scan
                            </button>
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="auctionNo">Auction No</label>
                        <select id="auctionNo" name="auctionNo">
                            <option value="">Loading auctions...</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="quantity">Quantity *</label>
                        <input type="number" id="quantity" name="quantity" min="1" value="1" required>
                    </div>
                </div>

                <div class="form-group">
                    <label for="productName">Item Name</label>
                    <input type="text" id="productName" name="productName">
                </div>

                <div class="grid-2">
                    <div class="form-group">
                        <label for="brand">Brand</label>
                        <input type="text" id="brand" name="brand">
                    </div>

                    <div class="form-group">
                        <label for="category">Category</label>
                        <input type="text" id="category" name="category">
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>Pricing Information</h2>
                
                <div class="grid-2">
                    <div class="form-group">
                        <label for="price">Price *</label>
                        <input type="number" id="price" name="price" step="0.01" min="0" required>
                    </div>

                    <div class="form-group">
                        <label for="currency">Currency *</label>
                        <select id="currency" name="currency" required>
                            <option value="CAD">CAD</option>
                            <option value="USD">USD</option>
                            <option value="EUR">EUR</option>
                            <option value="GBP">GBP</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="website">Source Website *</label>
                        <select id="website" name="website" required>
                            <option value="other">Other</option>
                            <option value="ebay">eBay</option>
                            <option value="amazon">Amazon</option>
                            <option value="walmart">Walmart</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="fourMorePrice">4more Price</label>
                        <input type="number" id="fourMorePrice" name="fourMorePrice" step="0.01" readonly>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>Product Details</h2>
                
                <div class="form-group">
                    <label for="description">Description</label>
                    <textarea id="description" name="description" rows="3"></textarea>
                </div>

                <div class="grid-2">
                    <div class="form-group">
                        <label for="weight">Weight</label>
                        <input type="text" id="weight" name="weight" placeholder="e.g., 1.5 kg">
                    </div>

                    <div class="form-group">
                        <label for="dimensions">Dimensions</label>
                        <input type="text" id="dimensions" name="dimensions" placeholder="L x W x H">
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>Inspection Details</h2>
                
                <div class="form-group">
                    <label for="inspectionCondition">Condition *</label>
                    <select id="inspectionCondition" name="inspectionCondition" required>
                        <option value="">Select condition</option>
                        <option value="Sealed">Sealed</option>
                        <option value="New-OpenBox">New-OpenBox</option>
                        <option value="ULN">ULN</option>
                        <option value="Lightly Used">Lightly Used</option>
                        <option value="Heavily Used">Heavily Used</option>
                        <option value="Missing Parts">Missing Parts</option>
                        <option value="Damaged">Damaged</option>
                        <option value="Not Working">Not Working</option>
                        <option value="Salvage">Salvage</option>
                        <option value="New">New</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="inspectionNotes">Inspection Notes</label>
                    <textarea id="inspectionNotes" name="inspectionNotes" rows="4"></textarea>
                </div>

                <div class="form-group">
                    <label>Inspection Photos</label>
                    <div style="border: 2px dashed var(--border-gray); padding: 40px; text-align: center; cursor: pointer;" onclick="document.getElementById('photos').click()">
                        <input type="file" id="photos" name="photos" multiple accept="image/*" style="display: none;">
                        <p>Click to upload photos</p>
                        <p id="photoCount"></p>
                    </div>
                </div>
            </div>

            <div style="display: flex; justify-content: space-between; margin-top: 30px;">
                <button type="button" class="btn btn-outline" onclick="clearForm()">
                    Clear Form
                </button>
                <button type="submit" class="btn btn-danger">
                    Submit to Airtable
                </button>
            </div>
        </form>
    </div>

    <div id="scannerModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeScanner()">&times;</span>
            <h3 id="scannerTitle">Scan Barcode</h3>
            <p id="scannerInstructions">Position the barcode within the frame</p>
            <div id="reader"></div>
            <div style="margin-top: 15px; text-align: center;">
                <button type="button" class="btn btn-outline" onclick="closeScanner()">Cancel</button>
            </div>
        </div>
    </div>

    <script>
        console.log('Script starting...');
        
        // Global variables
        let html5QrcodeScanner = null;
        let currentField = null;
        let scrapedImages = [];
        
        // Show warning message
        function showWarning(message) {
            const warningMsg = document.getElementById('warningMessage');
            warningMsg.textContent = message;
            warningMsg.style.display = 'block';
            setTimeout(function() {
                warningMsg.style.display = 'none';
            }, 10000);
        }
        
        // Barcode Scanner Functions
        function openScanner(fieldId) {
            console.log('Opening scanner for field:', fieldId);
            currentField = fieldId;
            
            // Update modal title based on field
            const title = document.getElementById('scannerTitle');
            const instructions = document.getElementById('scannerInstructions');
            
            if (fieldId === 'sku') {
                title.textContent = 'Scan SKU Barcode';
                instructions.textContent = 'Position the SKU barcode within the frame';
            } else if (fieldId === 'shelfCode') {
                title.textContent = 'Scan Shelf Location Code';
                instructions.textContent = 'Position the shelf location barcode/QR code within the frame';
            }
            
            // Show modal
            document.getElementById('scannerModal').style.display = 'block';
            
            // Initialize scanner
            startScanner();
        }
        
        function startScanner() {
            if (html5QrcodeScanner) {
                return; // Scanner already initialized
            }
            
            try {
                html5QrcodeScanner = new Html5Qrcode("reader");
                
                // Configure scanner options
                const config = {
                    fps: 10,
                    qrbox: { width: 250, height: 250 },
                    rememberLastUsedCamera: true,
                    // Support both QR codes and various barcode formats
                    formatsToSupport: [
                        Html5QrcodeSupportedFormats.CODE_128,
                        Html5QrcodeSupportedFormats.CODE_93,
                        Html5QrcodeSupportedFormats.CODE_39,
                        Html5QrcodeSupportedFormats.CODABAR,
                        Html5QrcodeSupportedFormats.EAN_13,
                        Html5QrcodeSupportedFormats.EAN_8,
                        Html5QrcodeSupportedFormats.ITF,
                        Html5QrcodeSupportedFormats.PDF_417,
                        Html5QrcodeSupportedFormats.QR_CODE,
                        Html5QrcodeSupportedFormats.UPC_A,
                        Html5QrcodeSupportedFormats.UPC_E
                    ]
                };
                
                // Success callback
                const onScanSuccess = (decodedText, decodedResult) => {
                    console.log('Scan successful:', decodedText);
                    console.log('Scan format:', decodedResult.result.format.formatName);
                    
                    // Set the value in the appropriate field
                    if (currentField) {
                        document.getElementById(currentField).value = decodedText;
                        
                        // Show success message
                        showSuccess(`Scanned: ${decodedText}`);
                        
                        // Close scanner
                        closeScanner();
                    }
                };
                
                // Error callback
                const onScanError = (errorMessage) => {
                    // Ignore frequent error messages during scanning
                    if (!errorMessage.includes('No QR code found')) {
                        console.log('Scan error:', errorMessage);
                    }
                };
                
                // Try to use back camera first, fall back to any available camera
                Html5Qrcode.getCameras().then(cameras => {
                    if (cameras && cameras.length) {
                        // Try to find back camera
                        let cameraId = cameras[0].id;
                        const backCamera = cameras.find(camera => 
                            camera.label.toLowerCase().includes('back') || 
                            camera.label.toLowerCase().includes('rear')
                        );
                        
                        if (backCamera) {
                            cameraId = backCamera.id;
                        }
                        
                        // Start scanning
                        html5QrcodeScanner.start(
                            cameraId,
                            config,
                            onScanSuccess,
                            onScanError
                        ).catch(err => {
                            console.error('Failed to start scanner:', err);
                            showError('Failed to start camera. Please ensure camera permissions are granted.');
                            closeScanner();
                        });
                    } else {
                        showError('No cameras found on this device.');
                        closeScanner();
                    }
                }).catch(err => {
                    console.error('Failed to get cameras:', err);
                    showError('Failed to access camera. Please ensure camera permissions are granted.');
                    closeScanner();
                });
                
            } catch (err) {
                console.error('Scanner initialization error:', err);
                showError('Failed to initialize scanner: ' + err.message);
                closeScanner();
            }
        }
        
        function closeScanner() {
            if (html5QrcodeScanner) {
                html5QrcodeScanner.stop().then(() => {
                    html5QrcodeScanner.clear();
                    html5QrcodeScanner = null;
                    currentField = null;
                    console.log('Scanner stopped and cleared');
                }).catch(err => {
                    console.error('Error stopping scanner:', err);
                    // Force cleanup even if stop fails
                    html5QrcodeScanner = null;
                    currentField = null;
                });
            }
            document.getElementById('scannerModal').style.display = 'none';
        }
        
        // Scrape product function
        async function scrapeProduct() {
            console.log('scrapeProduct called');
            
            const url = document.getElementById('url').value;
            if (!url) {
                showError('Please enter a URL first');
                return;
            }

            const scrapeBtn = document.getElementById('scrapeBtn');
            const loadingMsg = document.getElementById('loadingMessage');
            const errorMsg = document.getElementById('errorMessage');
            const warningMsg = document.getElementById('warningMessage');
            const scrapedInfo = document.getElementById('scrapedInfo');

            scrapeBtn.disabled = true;
            scrapeBtn.textContent = 'Scraping...';
            loadingMsg.style.display = 'block';
            errorMsg.style.display = 'none';
            warningMsg.style.display = 'none';
            scrapedInfo.style.display = 'none';

            try {
                const response = await fetch('/scrape', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url: url })
                });

                const data = await response.json();
                console.log('Scrape response:', data);

                if (data.error) {
                    throw new Error(data.error);
                }
                
                // Check if Amazon blocked the request
                if (data.blocked) {
                    showWarning(data.message || 'Amazon detected automated access. You may need to enter details manually.');
                    
                    // Show debug info if available
                    if (data.debug_info) {
                        const debugDiv = document.getElementById('debugInfo');
                        debugDiv.innerHTML = '<strong>Debug Info:</strong><br>' + 
                            'Status: ' + data.debug_info.status + '<br>' +
                            'Response Length: ' + data.debug_info.response_length + ' chars<br>' +
                            'Robot Check: ' + data.debug_info.robot_check + '<br>' +
                            'Captcha: ' + data.debug_info.captcha;
                        debugDiv.style.display = 'block';
                    }
                }

                // Fill form fields even if partially scraped
                let hasData = false;
                
                if (data.price && data.price !== "Price not found") {
                    document.getElementById('price').value = data.price;
                    hasData = true;
                }
                if (data.currency) {
                    document.getElementById('currency').value = data.currency;
                }
                if (data.name && data.name !== "Product name not found") {
                    document.getElementById('productName').value = data.name;
                    hasData = true;
                }
                if (data.brand) {
                    document.getElementById('brand').value = data.brand;
                    hasData = true;
                }
                if (data.gtin) {
                    document.getElementById('gtin').value = data.gtin;
                }
                if (data.description && data.description !== "Description not found") {
                    document.getElementById('description').value = data.description;
                }
                if (data.weight && data.weight !== "Weight not found") {
                    document.getElementById('weight').value = data.weight;
                }
                if (data.dimensions && data.dimensions.raw && data.dimensions.raw !== "Dimensions not found") {
                    document.getElementById('dimensions').value = data.dimensions.raw;
                }

                // Store scraped images
                scrapedImages = data.images || [];

                // Display scraped info
                let html = '<div>';
                if (data.name && data.name !== "Product name not found") {
                    html += '<p><strong>Product:</strong> ' + data.name + '</p>';
                }
                if (data.brand) {
                    html += '<p><strong>Brand:</strong> ' + data.brand + '</p>';
                }
                if (data.price && data.price !== "Price not found") {
                    html += '<p><strong>Price:</strong> ' + data.currency + ' ' + data.price + '</p>';
                }
                
                if (scrapedImages.length > 0) {
                    html += '<p><strong>Images (' + scrapedImages.length + '):</strong></p>';
                    html += '<div class="scraped-images">';
                    scrapedImages.slice(0, 12).forEach(function(img, index) {
                        html += '<div class="image-container">';
                        html += '<input type="checkbox" id="img_' + index + '" name="selectedImages" value="' + img + '" checked>';
                        html += '<img src="' + img + '" alt="Product ' + (index + 1) + '">';
                        html += '</div>';
                    });
                    html += '</div>';
                }
                html += '</div>';

                document.getElementById('scrapedDetails').innerHTML = html;
                scrapedInfo.style.display = 'block';

                if (hasData) {
                    showSuccess('Product information scraped successfully!');
                } else if (data.blocked) {
                    showWarning('Limited data extracted due to anti-bot protection. Please verify and complete the form manually.');
                } else {
                    showWarning('Limited product information found. Please complete the form manually.');
                }

            } catch (error) {
                console.error('Scrape error:', error);
                showError('Error scraping product: ' + error.message);
            } finally {
                loadingMsg.style.display = 'none';
                scrapeBtn.disabled = false;
                scrapeBtn.textContent = 'Scrape Info';
            }
        }

        // Other functions
        function showSuccess(message) {
            const successMsg = document.getElementById('successMessage');
            successMsg.textContent = message;
            successMsg.style.display = 'block';
            setTimeout(function() {
                successMsg.style.display = 'none';
            }, 5000);
        }

        function showError(message) {
            const errorMsg = document.getElementById('errorMessage');
            errorMsg.textContent = message;
            errorMsg.style.display = 'block';
            setTimeout(function() {
                errorMsg.style.display = 'none';
            }, 15000);
        }

        function clearForm() {
            document.getElementById('inventoryForm').reset();
            document.getElementById('scrapedInfo').style.display = 'none';
            scrapedImages = [];
        }

        // Handle photo selection
        document.getElementById('photos').addEventListener('change', function(e) {
            const count = e.target.files.length;
            document.getElementById('photoCount').textContent = count > 0 ? count + ' photo(s) selected' : '';
        });

        // Form submission
        document.getElementById('inventoryForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('Form submitted');
            
            const submitBtn = e.target.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            
            try {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Submitting...';
                
                // Create FormData to handle file uploads
                const formData = new FormData(e.target);
                
                // Add selected images from scraping
                const checkboxes = document.querySelectorAll('input[name="selectedImages"]:checked');
                checkboxes.forEach(function(checkbox) {
                    formData.append('selectedImages', checkbox.value);
                });
                
                const response = await fetch('/submit', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showSuccess(result.message || 'Item submitted successfully!');
                    // Optionally clear form after successful submission
                    // clearForm();
                } else {
                    showError('Error: ' + (result.error || 'Unknown error occurred'));
                }
                
            } catch (error) {
                console.error('Submit error:', error);
                showError('Error submitting form: ' + error.message);
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });

        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM loaded');
            
            // Add click event to scrape button
            const scrapeBtn = document.getElementById('scrapeBtn');
            if (scrapeBtn) {
                scrapeBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    scrapeProduct();
                });
            }
            
            // Load auctions
            fetch('/get-auctions')
                .then(response => response.json())
                .then(data => {
                    const select = document.getElementById('auctionNo');
                    select.innerHTML = '<option value="">Select an auction</option>';
                    if (data.success && data.auctions) {
                        data.auctions.forEach(function(auction) {
                            const option = document.createElement('option');
                            option.value = auction.id;
                            option.textContent = auction.name;
                            select.appendChild(option);
                        });
                    }
                })
                .catch(error => console.error('Error loading auctions:', error));
        });
        
        // Close scanner modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('scannerModal');
            if (event.target == modal) {
                closeScanner();
            }
        }
        
        console.log('Script loaded successfully');
    </script>
</body>
</html>
'''


class ProductScraper:
    def __init__(self):
        # Enhanced headers for better Amazon compatibility
        self.session = requests.Session()

        # Rotate user agents to avoid detection
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]

        self.headers = {
            'User-Agent': random.choice(user_agents),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"'
        }

        self.session.headers.update(self.headers)

    def scrape_product(self, url):
        try:
            # Add delay to avoid rate limiting (especially for Amazon)
            # Random delay between 1-3 seconds
            time.sleep(random.uniform(1, 3))

            # Follow redirects and get final URL
            response = self.session.get(
                url, timeout=15, allow_redirects=True)
            response.raise_for_status()

            # Update URL to the final redirected URL
            url = response.url

            # Debug info
            debug_info = {
                'status': response.status_code,
                'response_length': len(response.text),
                'robot_check': 'robot check' in response.text.lower(),
                'captcha': 'captcha' in response.text.lower()
            }

            # Save response for debugging (optional - comment out in production)
            # with open('last_scrape_response.html', 'w', encoding='utf-8') as f:
            #     f.write(response.text)

            # Check if we're getting blocked
            if 'Robot Check' in response.text or 'captcha' in response.text.lower():
                print("⚠️ Amazon detected bot activity - showing CAPTCHA page")
                return {
                    'name': 'Product name not found',
                    'brand': '',
                    'gtin': '',
                    'description': 'Amazon blocked automated access. Please enter details manually.',
                    'images': [],
                    'price': 'Price not found',
                    'currency': 'CAD' if 'amazon.ca' in url else 'USD',
                    'source': url,
                    'weight': 'Weight not found',
                    'dimensions': {'raw': 'Dimensions not found', 'length': None, 'width': None, 'height': None, 'unit': None},
                    'blocked': True,
                    'message': 'Amazon detected automated access. Please enter product details manually.',
                    'debug_info': debug_info
                }

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract data in order, storing name for dimension extraction
            name = self.extract_name(soup)
            self._last_product_name = name  # Store for dimension extraction

            # Store soup for currency extraction context
            price = self.extract_price(soup)
            currency = self.extract_currency(soup, url)

            product_data = {
                'name': name,
                'brand': self.extract_brand(soup, name),
                'gtin': self.extract_gtin(soup),
                'description': self.extract_description(soup),
                'images': self.extract_images(soup, url),
                'price': price,
                'currency': currency,
                'source': url,
                'weight': self.extract_weight(soup),
                'dimensions': self.extract_dimensions(soup),
                'blocked': False
            }

            # If weight not found but title contains weight info, extract it
            if product_data['weight'] == "Weight not found" and any(unit in name.lower() for unit in ['oz', 'fl', 'lb', 'g', 'kg', 'ml']):
                weight_patterns = [
                    r'(\d+\.?\d*)\s*(fl\.?\s*oz|fluid\s*ounces?)',
                    r'(\d+\.?\d*)\s*(oz|ounces?)\b',
                    r'(\d+\.?\d*)\s*(ml|mL|milliliters?)',
                    r'(\d+\.?\d*)\s*(g|grams?)\b',
                    r'(\d+\.?\d*)\s*(lbs?|pounds?)\b'
                ]
                for pattern in weight_patterns:
                    weight_match = re.search(pattern, name, re.IGNORECASE)
                    if weight_match:
                        product_data['weight'] = f"{weight_match.group(1)} {weight_match.group(2)}"
                        break

            # Debug: print what we found
            print(f"\n{'='*60}")
            print(f"🔍 Scraping Results for: {url[:60]}...")
            print(f"{'='*60}")
            print(f"📦 Product: {product_data['name'][:80]}...")
            print(f"🏷️  Brand: {product_data['brand'] or 'Not found'}")
            print(f"📊 GTIN/UPC/EAN: {product_data['gtin'] or 'Not found'}")
            print(f"💰 Price: {product_data['price']}")
            print(f"💱 Currency: {product_data['currency']}")
            print(f"📝 Description: {product_data['description'][:100]}...")
            print(f"🖼️  Images: {len(product_data['images'])} found")
            if product_data['images']:
                print(f"   First image: {product_data['images'][0][:80]}...")
            print(f"📏 Dimensions: {product_data['dimensions']['raw']}")
            print(f"⚖️  Weight: {product_data['weight']}")
            print(f"🤖 Blocked: {product_data['blocked']}")
            print(f"{'='*60}\n")

            return product_data

        except requests.exceptions.Timeout:
            print(f"⏱️ Request timed out for {url}")
            return {
                'name': 'Product name not found',
                'brand': '',
                'gtin': '',
                'description': 'Request timed out. The site may be slow or blocking automated access.',
                'images': [],
                'price': 'Price not found',
                'currency': 'USD',
                'source': url,
                'weight': 'Weight not found',
                'dimensions': {'raw': 'Dimensions not found', 'length': None, 'width': None, 'height': None, 'unit': None},
                'error': 'Request timed out'
            }
        except Exception as e:
            print(f"❌ Error scraping {url}: {str(e)}")
            raise Exception(f"Failed to scrape URL: {str(e)}")

    def extract_name(self, soup):
        # Try common patterns for product names
        selectors = [
            # Amazon specific - try these first
            'span#productTitle',
            'h1#title span',
            'h1.a-size-large',
            'h1[data-automation-id="title"]',
            # General patterns
            'h1',
            '[itemprop="name"]',
            '.product-name',
            '.product-title',
            '#product-title',
            '[data-testid="product-title"]',
            '.pdp-product-title',
            'h1.title',
            # eBay specific
            'h1.x-item-title__mainTitle',
            '.x-item-title h1',
            'h1 span.ux-textspans--BOLD',
            # Walmart
            'h1[itemprop="name"]',
            'h1.prod-ProductTitle',
            # Newegg
            'h1.product-title',
            # General
            'h1.product_title',
            '.product-name h1'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                name = element.get_text(strip=True)
                if name and len(name) > 5:  # Ensure it's a real product name
                    return name

        # Fallback to page title
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            # Clean up common title patterns
            title_text = re.sub(r'\s*-\s*Amazon\.ca.*$', '', title_text)
            title_text = re.sub(r'\s*\|\s*.*$', '', title_text)
            if title_text:
                return title_text

        return "Product name not found"

    def extract_brand(self, soup, product_name=""):
        # First try JSON-LD structured data
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if 'brand' in data:
                        brand_data = data['brand']
                        if isinstance(brand_data, dict) and 'name' in brand_data:
                            return brand_data['name']
                        elif isinstance(brand_data, str):
                            return brand_data
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'brand' in item:
                            brand_data = item['brand']
                            if isinstance(brand_data, dict) and 'name' in brand_data:
                                return brand_data['name']
                            elif isinstance(brand_data, str):
                                return brand_data
            except:
                pass

        # Try common brand selectors
        brand_selectors = [
            # Amazon specific
            'a#bylineInfo',
            'span.by-line a',
            'div.bylineInfo span.a-size-base',
            'a[id^="brand"]',
            'span.po-brand span.po-break-word',
            'tr.po-brand td.po-break-word span',
            # General
            '[itemprop="brand"]',
            '.product-brand',
            '.brand-name',
            '[data-testid="brand-name"]',
            '.product-brand-name',
            # Walmart specific
            '[data-testid="product-brand"]',
            'a[link-identifier="brandName"]',
            '.product-brand-title',
            # eBay specific
            '.ux-textspans--BOLD:contains("Brand")',
            'span[itemprop="brand"]',
            '.ux-layout-section__row:contains("Brand") .ux-textspans--BOLD',
            # General patterns
            'span:contains("Brand:") + span',
            'td:contains("Brand") + td',
            '.brand',
            '.manufacturer'
        ]

        for selector in brand_selectors:
            element = soup.select_one(selector)
            if element:
                brand_text = element.get_text(strip=True)
                # Clean up common patterns
                brand_text = re.sub(
                    r'^(Brand:|by|Visit the|Store)', '', brand_text, flags=re.IGNORECASE).strip()
                # Reasonable brand name length
                if brand_text and len(brand_text) < 50 and brand_text not in ['Unknown', 'N/A']:
                    return brand_text

        # Check Amazon's product details table
        details_table = soup.select(
            'table.prodDetTable tr, div.product-facts-detail')
        for row in details_table:
            text = row.get_text()
            if 'brand' in text.lower():
                # Extract the value after "Brand"
                parts = text.split(':')
                if len(parts) > 1:
                    brand = parts[1].strip()
                    if brand and len(brand) < 50:
                        return brand

        # Try to find brand in specification tables
        spec_selectors = [
            '.product-specifications',
            '[data-testid="product-specifications"]',
            '.specification-table',
            'table.product-specification-table',
            '.ux-layout-section-evo__item',
            '.ux-layout-section__row'
        ]

        for selector in spec_selectors:
            specs = soup.select(selector)
            for spec in specs:
                spec_text = spec.get_text()
                # Look for "Brand: [brand name]" pattern
                brand_match = re.search(
                    r'Brand[:\s]+([^\n\r]+)', spec_text, re.IGNORECASE)
                if brand_match:
                    brand = brand_match.group(1).strip()
                    if brand and len(brand) < 50:
                        return brand

        # Try to extract brand from product name (first word often is brand)
        if product_name and product_name != "Product name not found":
            # Common patterns where brand is at the beginning
            words = product_name.split()
            if words:
                first_word = words[0]
                # Check if first word looks like a brand (capitalized, not too long)
                if len(first_word) > 2 and len(first_word) < 20 and first_word[0].isupper():
                    # Avoid common non-brand words
                    non_brand_words = [
                        'New', 'The', 'Premium', 'Professional', 'Original', 'Genuine', 'Authentic']
                    if first_word not in non_brand_words:
                        return first_word

        return ""  # Return empty string if brand not found

    def extract_gtin(self, soup):
        # First try JSON-LD structured data
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # Check for gtin, gtin13, gtin12, gtin8, isbn
                    for gtin_key in ['gtin', 'gtin13', 'gtin12', 'gtin8', 'isbn', 'ean', 'upc']:
                        if gtin_key in data:
                            return str(data[gtin_key])
                    # Check in offers
                    if 'offers' in data and isinstance(data['offers'], dict):
                        for gtin_key in ['gtin', 'gtin13', 'gtin12', 'gtin8', 'isbn', 'ean', 'upc']:
                            if gtin_key in data['offers']:
                                return str(data['offers'][gtin_key])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            for gtin_key in ['gtin', 'gtin13', 'gtin12', 'gtin8', 'isbn', 'ean', 'upc']:
                                if gtin_key in item:
                                    return str(item[gtin_key])
            except:
                pass

        # Try common GTIN/UPC/EAN selectors
        gtin_selectors = [
            '[itemprop="gtin"]',
            '[itemprop="gtin13"]',
            '[itemprop="gtin12"]',
            '[itemprop="gtin8"]',
            '[itemprop="isbn"]',
            '.product-upc',
            '.product-ean',
            '.product-gtin',
            '.product-barcode',
            # Amazon specific - in product details
            'div.product-facts-detail',
            'table.prodDetTable',
            'div#detailBullets_feature_div span.a-list-item',
            # Walmart specific
            '[data-testid="product-upc"]',
            'div:contains("UPC") + div',
            # eBay specific
            'span:contains("UPC:") + span',
            'span:contains("EAN:") + span',
            'span:contains("ISBN:") + span',
            '.ux-textspans:contains("UPC")',
            '.ux-textspans:contains("EAN")',
        ]

        for selector in gtin_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    # Look for various GTIN patterns
                    patterns = [
                        r'UPC[:\s]+(\d{12})',
                        r'EAN[:\s]+(\d{13})',
                        r'GTIN[:\s]+(\d{8,14})',
                        r'ISBN-13[:\s]+(\d{13})',
                        r'ISBN-10[:\s]+(\d{10})',
                        r'ASIN[:\s]+([A-Z0-9]{10})',
                        # Just numbers that look like UPC/EAN
                        r'\b(\d{12,13})\b'
                    ]

                    for pattern in patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            return match.group(1)
            except:
                pass

        # Amazon specific - check product details section
        detail_bullets = soup.select(
            'div#detailBullets_feature_div span.a-list-item')
        for bullet in detail_bullets:
            text = bullet.get_text()
            if any(term in text for term in ['ASIN', 'UPC', 'EAN', 'ISBN']):
                # Extract the value
                parts = text.split(':')
                if len(parts) > 1:
                    value = parts[1].strip()
                    # Clean up the value
                    value = re.sub(r'[^\w\d]', '', value)
                    # Valid lengths for ASIN, UPC, EAN
                    if value and len(value) in [10, 12, 13]:
                        return value

        return ""  # Return empty string if GTIN not found

    def extract_description(self, soup):
        # Try common patterns for descriptions
        selectors = [
            # Amazon specific
            'div#feature-bullets ul',
            'div.feature ul li',
            'div#productDescription',
            'div#productDescription_feature_div',
            # General
            '[itemprop="description"]',
            '.product-description',
            '.product-details',
            '#product-description',
            '[data-testid="product-description"]',
            '.pdp-product-description',
            '.description',
            # eBay specific
            '.x-item-description iframe',
            '.ux-section--description',
            'div[data-testid="x-item-description"]',
            '.d-item-description',
            # Specific sites
            '.product-overview',
            '.product-details-description',
            'div[data-cy="product-description"]',
            '.product-info-section'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Handle Amazon bullet points
                if element.name == 'ul':
                    bullets = element.find_all('li')
                    if bullets:
                        description = ' '.join(
                            [li.get_text(strip=True) for li in bullets[:5]])
                        return description[:500]
                # Handle eBay iframe description
                elif element.name == 'iframe' and element.get('src'):
                    return "Full description available in item listing"
                else:
                    # Limit to 500 chars
                    return element.get_text(strip=True)[:500]

        # Try meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '')[:500]

        # Try og:description
        og_desc = soup.find('meta', {'property': 'og:description'})
        if og_desc:
            return og_desc.get('content', '')[:500]

        return "Description not found"

    def extract_images(self, soup, base_url):
        images = []

        # Amazon specific image extraction
        if 'amazon' in base_url:
            # Try to find images in the image block
            image_selectors = [
                'div#imageBlock img',
                'div#main-image-container img',
                'div.imgTagWrapper img',
                'img.a-dynamic-image',
                'img[data-a-image-name="landingImage"]',
                'div#altImages img',
                'div.imageThumbnail img'
            ]

            for selector in image_selectors:
                elements = soup.select(selector)
                for element in elements:
                    # Try different attributes
                    src = None
                    for attr in ['src', 'data-src', 'data-old-hires', 'data-a-dynamic-image']:
                        if element.get(attr):
                            if attr == 'data-a-dynamic-image':
                                # This attribute contains JSON with multiple sizes
                                try:
                                    img_data = json.loads(element.get(attr))
                                    # Get the largest image
                                    if img_data:
                                        src = list(img_data.keys())[0]
                                        break
                                except:
                                    pass
                            else:
                                src = element.get(attr)
                                break

                    if src and not src.startswith('data:'):
                        if src.startswith('//'):
                            src = 'https:' + src
                        absolute_url = urljoin(base_url, src)
                        if absolute_url not in images and not absolute_url.endswith('.gif'):
                            images.append(absolute_url)

        # General image extraction for other sites
        else:
            # Try common patterns for product images
            selectors = [
                'img[itemprop="image"]',
                '.product-image img',
                '.product-photo img',
                '.gallery-image img',
                '[data-testid="product-image"] img',
                '.pdp-image img',
                '.product-images img',
                # eBay specific
                '.ux-image-carousel-item img',
                '.ux-image-grid-item img',
                'button.ux-image-grid-item img',
                '.ux-image-carousel img',
                'div[data-testid="ux-image-carousel"] img',
                '.merch-image-grid img',
                # Walmart
                'img.hover-zoom-hero-image',
                'img[data-testid="hero-image"]',
                # General e-commerce
                '.product-image-main img',
                '.ProductImage img',
                'picture img',
                '.gallery img',
                '.thumbnail img'
            ]

            for selector in selectors:
                elements = soup.select(selector)
                for element in elements:
                    # Check multiple attributes for image source
                    src = (element.get('src') or
                           element.get('data-src') or
                           element.get('data-lazy-src') or
                           element.get('data-original') or
                           element.get('data-zoom-image'))

                    if src and src.startswith('data:'):
                        # Skip base64 encoded placeholder images
                        continue

                    if src:
                        # Clean up the URL
                        src = src.strip()
                        if src.startswith('//'):
                            src = 'https:' + src
                        absolute_url = urljoin(base_url, src)
                        if absolute_url not in images and not absolute_url.endswith('.gif'):
                            images.append(absolute_url)

        # Try to find high-res images in JSON-LD data
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if 'image' in data:
                        img_data = data['image']
                        if isinstance(img_data, str):
                            images.append(img_data)
                        elif isinstance(img_data, list):
                            images.extend(img_data)
            except:
                pass

        # Remove duplicates while preserving order
        seen = set()
        unique_images = []
        for img in images:
            if img not in seen:
                seen.add(img)
                unique_images.append(img)

        return unique_images[:10]  # Return max 10 images

    def extract_price(self, soup):
        # First try JSON-LD structured data (most reliable)
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if 'offers' in data and 'price' in data['offers']:
                        price = str(data['offers']['price'])
                        # Ensure it has decimal places
                        if '.' not in price and price.isdigit():
                            price = price + '.00'
                        return price
                    elif 'price' in data:
                        price = str(data['price'])
                        if '.' not in price and price.isdigit():
                            price = price + '.00'
                        return price
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            if 'offers' in item and isinstance(item['offers'], dict) and 'price' in item['offers']:
                                price = str(item['offers']['price'])
                                if '.' not in price and price.isdigit():
                                    price = price + '.00'
                                return price
                            elif 'price' in item:
                                price = str(item['price'])
                                if '.' not in price and price.isdigit():
                                    price = price + '.00'
                                return price
            except:
                pass

        # Try common patterns for prices
        selectors = [
            # Amazon specific - enhanced selectors
            'span.a-price.a-text-price.a-size-medium.apexPriceToPay',
            'span.a-price-whole',
            '.a-price .a-offscreen',
            'span.a-price > span.a-offscreen',
            'span[class*="price"] > span.a-offscreen',
            'div.a-section.a-spacing-none.aok-align-center span.a-price-whole',
            'span.priceToPay',
            '.reinventPricePriceToPayMargin span.a-price-whole',
            # General
            '[itemprop="price"]',
            '.price',
            '.product-price',
            '.current-price',
            '[data-testid="product-price"]',
            '.pdp-price',
            'span.price',
            '.price-now',
            # eBay specific
            '.x-price-primary span[itemprop="price"]',
            '.x-price-primary .ux-textspans',
            'span.ux-textspans[itemprop="price"]',
            '.x-bin-price__content',
            '.x-buybox-price',
            # Walmart
            'span[itemprop="price"]',
            '.price-characteristic',
            '[data-automation-id="product-price"]',
        ]

        # Try each selector
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Check if it's a meta tag
                if element.name == 'meta':
                    price = element.get('content', '')
                    if price and price.replace('.', '').replace(',', '').isdigit():
                        return price.replace(',', '')
                else:
                    price_text = element.get_text(strip=True)
                    # Clean and extract price
                    # Remove currency codes
                    price_text = re.sub(r'^[A-Z]{3}\s*', '', price_text)
                    price_text = re.sub(
                        r'[\$£€¥₹]\s*', '', price_text)  # Remove symbols

                    # Extract numeric price
                    price_match = re.search(
                        r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', price_text)
                    if price_match:
                        price = price_match.group(1).replace(',', '')
                        # Ensure it has decimal places
                        if '.' not in price:
                            price = price + '.00'
                        return price

        # Amazon-specific: Try whole + fraction approach
        amazon_whole = soup.select_one('span.a-price-whole')
        if amazon_whole:
            whole_text = amazon_whole.get_text(strip=True).rstrip('.')

            # Look for fraction
            amazon_fraction = soup.select_one('span.a-price-fraction')
            if amazon_fraction:
                fraction_text = amazon_fraction.get_text(strip=True)
                return f"{whole_text}.{fraction_text}"
            else:
                # Check if there's a decimal in the parent
                parent = amazon_whole.parent
                if parent:
                    parent_text = parent.get_text(strip=True)
                    price_match = re.search(
                        r'(\d{1,3}(?:,\d{3})*\.?\d*)', parent_text)
                    if price_match:
                        price = price_match.group(1).replace(',', '')
                        if '.' not in price:
                            price = price + '.00'
                        return price

                return whole_text + '.00'

        return "Price not found"

    def extract_currency(self, soup, url=''):
        # Check URL domain first for Amazon
        if 'amazon.ca' in url:
            return 'CAD'
        elif 'amazon.com' in url:
            return 'USD'
        elif 'amazon.co.uk' in url:
            return 'GBP'
        elif 'amazon.de' in url or 'amazon.fr' in url or 'amazon.es' in url or 'amazon.it' in url:
            return 'EUR'
        elif 'amazon.co.jp' in url:
            return 'JPY'
        elif 'amazon.in' in url:
            return 'INR'
        elif 'amazon.com.au' in url:
            return 'AUD'

        # Try to find currency in structured data
        currency_meta = soup.find('meta', {'itemprop': 'priceCurrency'})
        if currency_meta:
            return currency_meta.get('content', 'USD')

        # Check JSON-LD structured data
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'offers' in data:
                    if 'priceCurrency' in data['offers']:
                        return data['offers']['priceCurrency']
            except:
                pass

        # Default based on domain
        if 'walmart.ca' in url:
            return 'CAD'
        elif 'ebay.ca' in url:
            return 'CAD'

        # Default to USD for most sites
        return 'USD'

    def extract_weight(self, soup):
        # Look for weight patterns
        weight_patterns = [
            r'weight[:\s]*(\d+\.?\d*)\s*(kg|g|lbs?|pounds?|ounces?|oz|fl\s*oz)',
            r'(\d+\.?\d*)\s*(kg|g|lbs?|pounds?|ounces?|oz|fl\s*oz)\s*weight',
            r'item\s*weight[:\s]*(\d+\.?\d*)\s*(kg|g|lbs?|pounds?|ounces?|oz|fl\s*oz)',
            r'shipping\s*weight[:\s]*(\d+\.?\d*)\s*(kg|g|lbs?|pounds?|ounces?|oz|fl\s*oz)',
            r'net\s*wt\.?\s*(\d+\.?\d*)\s*(kg|g|lbs?|pounds?|ounces?|oz|fl\s*oz)',
            r'(\d+\.?\d*)\s*(fl\s*oz|fluid\s*ounces?)'
        ]

        # Check common weight containers
        weight_selectors = [
            '.product-weight',
            '[itemprop="weight"]',
            # Amazon specific
            'table.prodDetTable tr',
            'div#detailBullets_feature_div span.a-list-item',
            'div.product-facts-detail',
            # General
            'td:contains("Weight")',
            'span:contains("Weight")',
        ]

        # Try selectors first
        for selector in weight_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text()
                for pattern in weight_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        return f"{match.group(1)} {match.group(2)}"

        # Check product title for weight
        if hasattr(self, '_last_product_name'):
            title_patterns = [
                r'(\d+\.?\d*)\s*(fl\.?\s*oz|fluid\s*ounces?)',
                r'(\d+\.?\d*)\s*(oz|ounces?)\b',
                r'(\d+\.?\d*)\s*(ml|mL|milliliters?)',
                r'(\d+\.?\d*)\s*(L|liters?)\b',
                r'(\d+\.?\d*)\s*(g|grams?)\b',
                r'(\d+\.?\d*)\s*(kg|kilograms?)\b',
                r'(\d+\.?\d*)\s*(lbs?|pounds?)\b'
            ]
            for pattern in title_patterns:
                match = re.search(
                    pattern, self._last_product_name, re.IGNORECASE)
                if match:
                    return f"{match.group(1)} {match.group(2)}"

        return "Weight not found"

    def extract_dimensions(self, soup):
        # Returns a dict with raw string and parsed dimensions
        dimensions = {
            'raw': 'Dimensions not found',
            'length': None,
            'width': None,
            'height': None,
            'unit': None
        }

        # Look for dimension patterns
        dim_patterns = [
            # L x W x H patterns
            r'(\d+\.?\d*)\s*["\']?\s*[Ll]\s*[x×]\s*(\d+\.?\d*)\s*["\']?\s*[Ww]\s*[x×]\s*(\d+\.?\d*)\s*["\']?\s*[Hh]\s*["\']?\s*(in|inches?|cm|mm)?',
            r'[Ll]ength[:\s]*(\d+\.?\d*).*[Ww]idth[:\s]*(\d+\.?\d*).*[Hh]eight[:\s]*(\d+\.?\d*)\s*(in|inches?|cm|mm)?',
            # Standard 3D patterns
            r'(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)\s*(in|inches?|cm|mm|m)?',
            r'dimensions?[:\s]*(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)\s*(cm|mm|in|inches?|m)?',
            # 2D patterns
            r'(\d+\.?\d*)["\'″]\s*[x×]\s*(\d+\.?\d*)["\'″]',
            r'(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)\s*(in|inches?|cm|mm)?'
        ]

        # Selectors for finding dimensions
        dim_selectors = [
            # Amazon specific
            'table.prodDetTable tr',
            'div#detailBullets_feature_div span.a-list-item',
            'div.product-facts-detail',
            # General
            '.product-dimensions',
            '[itemprop="dimensions"]',
            'td:contains("Dimensions")',
            'span:contains("Dimensions")',
        ]

        # Try selectors first
        for selector in dim_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text()
                for pattern in dim_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        dimensions['raw'] = match.group(0).strip()
                        groups = match.groups()

                        if len(groups) >= 2:
                            try:
                                dimensions['length'] = float(groups[0])
                                dimensions['width'] = float(groups[1])
                                if len(groups) >= 3 and groups[2] and not groups[2] in ['in', 'cm', 'mm', 'inches', 'm']:
                                    dimensions['height'] = float(groups[2])
                                if groups[-1] in ['in', 'cm', 'mm', 'inches', 'm']:
                                    dimensions['unit'] = groups[-1]
                                else:
                                    dimensions['unit'] = 'in'
                            except (ValueError, IndexError):
                                pass

                        return dimensions

        # Check product title
        if hasattr(self, '_last_product_name'):
            for pattern in dim_patterns[-2:]:  # Check 2D patterns in title
                match = re.search(
                    pattern, self._last_product_name, re.IGNORECASE)
                if match:
                    dimensions['raw'] = match.group(0).strip()
                    return dimensions

        return dimensions


# Rest of your Flask routes remain the same...
@app.route('/test-airtable', methods=['GET'])
def test_airtable():
    """Test Airtable connection and list tables"""
    try:
        if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
            return jsonify({"error": "Airtable not configured"}), 500

        headers = {
            'Authorization': f'Bearer {AIRTABLE_API_KEY}',
            'Content-Type': 'application/json'
        }

        # Try to access the Auctions table
        url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/Auctions'
        params = {'maxRecords': 1}

        response = requests.get(url, headers=headers, params=params)

        result = {
            "airtable_connected": response.status_code == 200,
            "auctions_table_exists": response.status_code == 200,
            "status_code": response.status_code
        }

        if response.status_code == 200:
            records = response.json().get('records', [])
            if records:
                fields = list(records[0].get('fields', {}).keys())
                result["auction_fields"] = fields
        else:
            result["error"] = response.text[:200]

        # Also test the Items table to see available fields
        items_url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}'
        items_response = requests.get(
            items_url, headers=headers, params={'maxRecords': 1})

        if items_response.status_code == 200:
            items_records = items_response.json().get('records', [])
            if items_records:
                items_fields = list(items_records[0].get('fields', {}).keys())
                result["items_table_fields"] = items_fields
                # Check for photo fields
                photo_fields = [f for f in items_fields if 'photo' in f.lower(
                ) or 'image' in f.lower() or 'attachment' in f.lower()]
                if photo_fields:
                    result["potential_photo_fields"] = photo_fields

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/check-config', methods=['GET'])
def check_config():
    """Check configuration status"""
    config = {
        "airtable_configured": bool(AIRTABLE_API_KEY and AIRTABLE_BASE_ID),
        "cloudinary_configured": bool(CLOUDINARY_AVAILABLE and CLOUDINARY_CLOUD_NAME),
        "cloudinary_available": CLOUDINARY_AVAILABLE
    }

    # Test if we can find the inspection photos field
    if config["airtable_configured"]:
        try:
            headers = {
                'Authorization': f'Bearer {AIRTABLE_API_KEY}',
                'Content-Type': 'application/json'
            }

            # Get schema for Items table
            url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}'
            response = requests.get(
                url, headers=headers, params={'maxRecords': 1})

            if response.status_code == 200:
                records = response.json().get('records', [])
                if records:
                    fields = list(records[0].get('fields', {}).keys())
                    # Show first 10 fields
                    config["items_fields_sample"] = fields[:10]
                    config["inspection_photos_field_exists"] = "Inspection Photos" in fields

                    # Find any attachment-type fields
                    attachment_fields = [f for f in fields if any(word in f.lower() for word in [
                                                                  'photo', 'image', 'attachment', 'picture', 'file'])]
                    if attachment_fields:
                        config["possible_attachment_fields"] = attachment_fields
        except Exception as e:
            config["field_check_error"] = str(e)

    return jsonify(config)


@app.route('/get-auctions', methods=['GET'])
def get_auctions():
    """Fetch active and future auctions from Airtable"""
    try:
        if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
            return jsonify({"error": "Airtable not configured"}), 500

        headers = {
            'Authorization': f'Bearer {AIRTABLE_API_KEY}',
            'Content-Type': 'application/json'
        }

        # CONFIGURATION: Update these based on your Auctions table structure
        auction_table = 'Auctions'  # Your auctions table name

        # First, let's try to get ALL auctions without any filter
        url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{auction_table}'

        print(f"\n=== Fetching ALL Auctions (no filter) ===")
        print(f"URL: {url}")

        # Get all auctions without filter to ensure the table exists
        params = {
            'maxRecords': 100,  # Get up to 100 auctions
            'sort[0][field]': 'Created',  # Sort by creation date
            'sort[0][direction]': 'desc'
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            records = response.json().get('records', [])
            auctions = []

            print(f"\nFound {len(records)} auction records")

            # Debug: Show first auction's fields
            if records:
                first_fields = records[0].get('fields', {})
                print("\nFirst auction has these fields:")
                for field_name in first_fields.keys():
                    print(f"  - {field_name}")

            for record in records:
                fields = record.get('fields', {})

                # Try multiple field names for auction identifier
                auction_name = (
                    fields.get('Auction Name') or
                    fields.get('Auction No') or
                    fields.get('Name') or
                    fields.get('Title') or
                    fields.get('Auction Number') or
                    fields.get('Number') or
                    fields.get('Auction') or
                    fields.get('Auction ID') or
                    fields.get('ID') or
                    f"Auction {record['id'][-6:]}"  # Fallback
                )

                # Get status - might be different field names
                status = (
                    fields.get('Status') or
                    fields.get('Auction Status') or
                    fields.get('State') or
                    'Unknown'
                )

                # Get date - might be different field names
                date = (
                    fields.get('Auction Date') or
                    fields.get('Date') or
                    fields.get('Start Date') or
                    fields.get('Created') or
                    ''
                )

                auction_data = {
                    'id': record['id'],
                    'name': str(auction_name),
                    'date': date,
                    'status': status
                }
                auctions.append(auction_data)

                # Debug first few auctions
                if len(auctions) <= 3:
                    print(f"  Auction: {auction_name} - Status: {status}")

            return jsonify({"success": True, "auctions": auctions})

        elif response.status_code == 404:
            error_msg = "Table 'Auctions' not found. Please check the table name."
            print(f"\nError: {error_msg}")
            return jsonify({
                "error": error_msg,
                "suggestion": "Make sure you have an 'Auctions' table in your Airtable base"
            }), 404

        else:
            error_data = response.json() if response.headers.get(
                'content-type') == 'application/json' else {}
            error_msg = f"Airtable API Error: {response.status_code} - {response.text[:200]}"
            print(f"\nError: {error_msg}")

            return jsonify({
                "error": "Failed to fetch auctions",
                "details": error_msg
            }), 500

    except Exception as e:
        print(f"\nException in get_auctions: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": str(e),
            "suggestion": "Check server console for details"
        }), 500


@app.route('/find-attachment-fields', methods=['GET'])
def find_attachment_fields():
    """Try to identify attachment fields by testing them"""
    try:
        if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
            return jsonify({"error": "Airtable not configured"}), 500

        headers = {
            'Authorization': f'Bearer {AIRTABLE_API_KEY}',
            'Content-Type': 'application/json'
        }

        # First get list of fields
        url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}'
        response = requests.get(url, headers=headers, params={'maxRecords': 1})

        if response.status_code != 200:
            return jsonify({"error": "Could not access table"}), 500

        records = response.json().get('records', [])
        if not records:
            return jsonify({"error": "No records found to analyze"}), 400

        fields = list(records[0].get('fields', {}).keys())

        # Filter to potential attachment fields
        potential_fields = [f for f in fields if any(word in f.lower() for word in [
                                                     'photo', 'image', 'attachment', 'file', 'picture', 'inspection'])]

        results = {
            "all_fields": fields,
            "potential_attachment_fields": potential_fields,
            "recommendation": None
        }

        # Look for most likely inspection photo field
        for field in potential_fields:
            if 'inspection' in field.lower() and ('photo' in field.lower() or 'image' in field.lower()):
                results["recommendation"] = field
                results["message"] = f"Found likely field: '{field}' - Update INSPECTION_PHOTOS_FIELD_NAME in the code to match"
                break

        if not results["recommendation"] and potential_fields:
            results["recommendation"] = potential_fields[0]
            results["message"] = f"No 'inspection photo' field found. Consider using: '{potential_fields[0]}'"
        elif not potential_fields:
            results["message"] = "No attachment-like fields found. Make sure you have an Attachment field in Airtable."

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/test-photo-field', methods=['GET'])
def test_photo_field():
    """Test if the Inspection Photos field can accept attachments"""
    try:
        if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
            return jsonify({"error": "Airtable not configured"}), 500

        headers = {
            'Authorization': f'Bearer {AIRTABLE_API_KEY}',
            'Content-Type': 'application/json'
        }

        # Get the field name from the configuration in submit()
        # This is hardcoded here but should match what's in submit()
        INSPECTION_PHOTOS_FIELD_NAME = "Inspection Photos"

        # Try to create a test record with a dummy photo URL
        test_data = {
            "fields": {
                "SKU": "TEST-PHOTO-" + datetime.now().strftime('%Y%m%d%H%M%S'),
                "Item Name": "Test Photo Upload",
                "Unit Retail Price": 0.01,
                "Quantity": 1,
                INSPECTION_PHOTOS_FIELD_NAME: [
                    {
                        "url": "https://via.placeholder.com/150"
                    }
                ]
            }
        }

        url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}'
        response = requests.post(url, headers=headers, json=test_data)

        result = {
            "test_status": "success" if response.status_code == 200 else "failed",
            "status_code": response.status_code,
            "field_name_tested": INSPECTION_PHOTOS_FIELD_NAME
        }

        if response.status_code == 200:
            # Delete the test record
            record_id = response.json().get('id')
            if record_id:
                delete_url = f"{url}/{record_id}"
                requests.delete(delete_url, headers=headers)
                result["test_record_deleted"] = True
            result["message"] = f"✓ '{INSPECTION_PHOTOS_FIELD_NAME}' field is configured correctly!"
        else:
            error_data = response.json()
            result["error"] = error_data
            result["message"] = f"❌ '{INSPECTION_PHOTOS_FIELD_NAME}' field is not configured correctly or doesn't exist"

            # Try to parse the error for more specific guidance
            if 'INVALID_VALUE_FOR_COLUMN' in str(error_data):
                result["suggestion"] = "The field exists but might not be an Attachment type"
            elif 'UNKNOWN_FIELD_NAME' in str(error_data):
                result["suggestion"] = f"The field '{INSPECTION_PHOTOS_FIELD_NAME}' doesn't exist in your table"

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        data = request.get_json()
        url = data.get('url')

        if not url:
            return jsonify({'error': 'URL is required'}), 400

        scraper = ProductScraper()
        product_data = scraper.scrape_product(url)

        return jsonify(product_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/submit', methods=['POST'])
def submit():
    # CONFIGURATION: Update these field names to match your Airtable table
    # IMPORTANT: These must match EXACTLY (including capitalization and spaces)
    PHOTOS_FIELD_NAME = "Item Photos"  # The attachment field for product images
    # The attachment field for inspection photos
    INSPECTION_PHOTOS_FIELD_NAME = "Inspection Photos"

    # To find your exact field names:
    # 1. Go to http://localhost:5000/test-airtable
    # 2. Look for "items_table_fields" in the response
    # 3. Update the field names above to match exactly
    #
    # Common field name variations to check:
    # - "Inspection Photos" vs "InspectionPhotos" vs "Inspection_Photos"
    # - "Inspection Photos" vs "Inspection Images" vs "Inspection Attachments"
    # - "Inspection Photos" vs "Photos" vs "Images"

    AUCTION_TABLE_NAME = "Auctions"  # The table name for auctions
    AUCTION_NAME_FIELD = "Auction Name"  # The field containing auction names

    try:
        # Check if Airtable credentials are configured
        if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
            return jsonify({
                "success": False,
                "error": "Airtable credentials not configured. Please check your .env file."
            })

        # Get form data
        form_data = request.form

        # Log form data for debugging
        print("\n" + "="*60)
        print("=== NEW SUBMISSION RECEIVED ===")
        print("="*60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n=== Form Data Received ===")
        for key, value in form_data.items():
            print(f"{key}: {value}")

        # Log selected images separately for debugging
        selected_images = form_data.getlist('selectedImages')
        print(f"\n=== Selected Images ({len(selected_images)}) ===")
        for idx, img in enumerate(selected_images):
            print(f"Image {idx + 1}: {img[:80]}..." if len(img)
                  > 80 else f"Image {idx + 1}: {img}")

        # Check specific fields
        print(f"\n=== Key Fields Check ===")
        print(f"Brand: '{form_data.get('brand')}'")
        print(f"Condition: '{form_data.get('inspectionCondition')}'")
        print(f"Store: '{form_data.get('store')}'")
        print(f"Auction No: '{form_data.get('auctionNo')}'")

        # Calculate 4more price
        price = float(form_data.get('price', 0))
        currency = form_data.get('currency')
        website = form_data.get('website')

        four_more_price = price
        if website == 'ebay':
            four_more_price = price * 1.2
        elif currency == 'USD':
            four_more_price = price * 1.5

        # Initialize additional_info list early to avoid reference errors
        additional_info = []

        # Start with absolute minimum fields and add one by one to identify the problem
        data = {
            "fields": {
                "SKU": form_data.get('sku'),
                "Item Name": form_data.get('productName') or "",
                "Unit Retail Price": price,
                "Quantity": int(form_data.get('quantity', 1))
            }
        }

        # Text fields - should be safe
        safe_fields = {
            "GTIN": form_data.get('gtin') or "",
            "Shelf Location": form_data.get('shelfCode') or "",
            "Description": form_data.get('description') or "",
            "Inspection Notes": form_data.get('inspectionNotes') or "",
            "Brand": form_data.get('brand') or ""  # Add Brand field
        }

        # Add safe fields
        for field, value in safe_fields.items():
            if value:  # Only add non-empty values
                data["fields"][field] = value

        # Fields that might be problematic
        # Try adding these one at a time to identify issues

        # 1. Try 4more Price (number field)
        try:
            data["fields"]["4more Price"] = four_more_price
            print(f"✓ Added 4more Price: {four_more_price}")
        except Exception as e:
            print(f"✗ Could not add 4more Price: {e}")

        # 2. Try Condition (might be single select)
        condition = form_data.get('inspectionCondition')
        if condition:
            try:
                data["fields"]["Condition"] = condition
                print(f"✓ Added Condition: {condition}")
            except Exception as e:
                print(f"✗ Could not add Condition: {e}")

        # 3. Try Item Type
        try:
            data["fields"]["Item Type"] = "Physical Goods"
            print(f"✓ Added Item Type: Physical Goods")
        except Exception as e:
            print(f"✗ Could not add Item Type: {e}")

        # 4. Try 4more Store (might be single select or text field)
        store_value = form_data.get('store')
        if store_value:
            try:
                data["fields"]["4more Store"] = store_value
                print(f"✓ Added 4more Store: {store_value}")
            except Exception as e:
                print(f"✗ Could not add 4more Store: {e}")
                # Add to additional info if field doesn't exist
                additional_info.append(f"4more Store: {store_value}")

        # 5. Handle Auction No as linked record
        auction_id = form_data.get('auctionNo')
        if auction_id:
            try:
                # Auction No is a linked record, so it needs an array of IDs
                data["fields"]["Auction No"] = [auction_id]
                print(f"✓ Added Auction No: {auction_id}")
            except Exception as e:
                print(f"✗ Could not add Auction No: {e}")
                additional_info.append(
                    f"Auction No: Selected but could not link")

        # Add all other data to description
        website_value = form_data.get('website')
        if website_value:
            additional_info.append(f"Scraping Website: {website_value}")

        category_value = form_data.get('category')
        if category_value:
            additional_info.append(f"Category: {category_value}")

        # Handle images - try to add to Photos field if it exists
        if selected_images:
            # Format images for Airtable attachment field
            # Airtable expects an array of objects with 'url' property
            image_attachments = []
            for img_url in selected_images:
                if img_url:  # Only add non-empty URLs
                    image_attachments.append({
                        "url": img_url
                    })

            # Try to add to Photos field (or whatever your image field is called)
            if image_attachments:
                try:
                    data["fields"][PHOTOS_FIELD_NAME] = image_attachments
                    print(
                        f"✓ Added {len(image_attachments)} product images to {PHOTOS_FIELD_NAME} field")
                    print(
                        f"  First image URL: {image_attachments[0]['url'][:80]}...")
                except Exception as e:
                    print(
                        f"✗ Could not add images to {PHOTOS_FIELD_NAME} field: {e}")
                    # If the field doesn't exist or there's an error, add URLs to description
                    additional_info.append(
                        f"\nProduct Images ({len(selected_images)}) - URLs stored in description:")
                    for i, img_url in enumerate(selected_images[:5], 1):
                        additional_info.append(f"{i}. {img_url}")
                    if len(selected_images) > 5:
                        additional_info.append(
                            f"... and {len(selected_images) - 5} more images")
            else:
                print("✗ No valid image URLs to add")

            # Also add a count to description for record keeping
            if len(image_attachments) > 0:
                additional_info.append(
                    f"\nProduct Images: {len(image_attachments)} images successfully added to Item Photos field")
            else:
                additional_info.append(
                    f"\nProduct Images: {len(selected_images)} scraped (none selected for upload)")
        else:
            print("ℹ️  No images selected by user")

        # Handle inspection photos
        inspection_files = request.files.getlist('photos')
        inspection_photos = []
        photo_count = 0

        print(f"\n=== Inspection Photos Processing ===")
        print(f"Number of files received: {len(inspection_files)}")
        print(
            f"Cloudinary configured: {bool(CLOUDINARY_AVAILABLE and CLOUDINARY_CLOUD_NAME)}")

        for idx, photo in enumerate(inspection_files):
            if photo and photo.filename:
                photo_count += 1
                print(f"\nProcessing photo {idx + 1}: {photo.filename}")

                # Check file size before reading
                photo.seek(0, 2)  # Seek to end
                file_size = photo.tell()
                photo.seek(0)  # Reset to beginning
                print(f"  File size: {file_size} bytes")

                # Upload to Cloudinary if configured
                if CLOUDINARY_AVAILABLE and CLOUDINARY_CLOUD_NAME:
                    try:
                        # Upload the photo to Cloudinary
                        print(f"  Uploading to Cloudinary...")
                        upload_result = cloudinary.uploader.upload(
                            photo,
                            folder="inspection_photos",  # Organize in folders
                            resource_type="auto",
                            allowed_formats=['jpg', 'jpeg',
                                             'png', 'gif', 'webp', 'bmp']
                        )

                        # Get the secure URL
                        photo_url = upload_result.get('secure_url')
                        if photo_url:
                            inspection_photos.append({"url": photo_url})
                            print(
                                f"  ✓ Upload successful: {photo_url[:80]}...")
                        else:
                            print(f"  ✗ No URL returned from Cloudinary")

                    except Exception as e:
                        print(f"  ✗ Upload failed: {str(e)}")
                        print(f"     Error type: {type(e).__name__}")
                        if hasattr(e, '__dict__'):
                            print(f"     Error details: {e.__dict__}")
                else:
                    print(f"  ⚠ Skipping - Cloudinary not configured")
                    if not CLOUDINARY_AVAILABLE:
                        print("     Cloudinary module not installed")
                    if not CLOUDINARY_CLOUD_NAME:
                        print("     Cloudinary credentials missing")

        print(f"\nTotal photos processed: {photo_count}")
        print(f"Successfully uploaded: {len(inspection_photos)}")

        # Try to add inspection photos to Airtable if we have URLs
        if inspection_photos:
            try:
                # Log the exact field name and data being sent
                print(f"\n📸 Attempting to add inspection photos to Airtable:")
                print(f"   Field name: '{INSPECTION_PHOTOS_FIELD_NAME}'")
                print(f"   Number of photos: {len(inspection_photos)}")
                print(f"   Photo URLs:")
                for i, photo in enumerate(inspection_photos):
                    print(f"     {i+1}. {photo['url'][:100]}...")

                data["fields"][INSPECTION_PHOTOS_FIELD_NAME] = inspection_photos
                print(f"✓ Photos added to data structure")
                additional_info.append(
                    f"\nInspection Photos: {len(inspection_photos)} uploaded successfully")
            except Exception as e:
                print(f"\n✗ Could not add photos to Airtable field: {e}")
                print(f"   Error type: {type(e).__name__}")
                additional_info.append(
                    f"\nInspection Photos: {len(inspection_photos)} uploaded to Cloudinary but not linked in Airtable")
                additional_info.append(
                    f"   Field name tried: '{INSPECTION_PHOTOS_FIELD_NAME}'")
                additional_info.append(f"   Error: {str(e)}")
        elif photo_count > 0:
            print(f"\n⚠ No photos uploaded - Cloudinary configuration issue")
            additional_info.append(
                f"\nInspection Photos: {photo_count} selected but not uploaded")
            if not CLOUDINARY_AVAILABLE:
                additional_info.append(
                    "Install cloudinary: pip install cloudinary")
            elif not CLOUDINARY_CLOUD_NAME:
                additional_info.append(
                    "Add Cloudinary credentials to .env file")
        else:
            print(f"\nℹ️  No inspection photos selected")

        # Add all additional info to description
        if additional_info:
            current_desc = data["fields"].get("Description", "")
            extra_text = "\n".join(additional_info)
            if current_desc:
                data["fields"]["Description"] = f"{current_desc}\n\n--- Additional Information ---\n{extra_text}"
            else:
                data["fields"]["Description"] = f"--- Additional Information ---\n{extra_text}"

        # Add weight, dimensions, and currency info to description
        extra_info = []

        # Add currency if not CAD
        if currency and currency != "CAD":
            extra_info.append(f"Currency: {currency}")

        # Add weight if available
        weight = form_data.get('weight')
        if weight and weight != "Weight not found":
            extra_info.append(f"Weight: {weight}")

        # Add dimensions if available
        dimensions = form_data.get('dimensions')
        if dimensions and dimensions != "Dimensions not found":
            extra_info.append(f"Dimensions: {dimensions}")

        # Add URL
        url = form_data.get('url')
        if url:
            extra_info.append(f"Source: {url}")

        # Append all extra info to description
        if extra_info:
            current_desc = data["fields"].get("Description", "")
            if current_desc:
                data["fields"]["Description"] = f"{current_desc}\n\n{chr(10).join(extra_info)}"
            else:
                data["fields"]["Description"] = chr(10).join(extra_info)

        # Remove empty string fields to avoid any issues
        data["fields"] = {k: v for k, v in data["fields"].items() if v != ""}

        print("\n=== Data being sent to Airtable ===")
        print(json.dumps(data, indent=2))
        print("\n=== Field Types ===")
        for field, value in data["fields"].items():
            print(f"{field}: {type(value).__name__} = {repr(value)}")

        # Special check for photo fields
        if INSPECTION_PHOTOS_FIELD_NAME in data["fields"]:
            photos = data["fields"][INSPECTION_PHOTOS_FIELD_NAME]
            print(f"\n📸 Inspection Photos Detail:")
            print(f"   Field name: '{INSPECTION_PHOTOS_FIELD_NAME}'")
            print(f"   Number of photos: {len(photos)}")
            print(f"   Data structure: {type(photos).__name__}")
            if photos:
                print(f"   First photo structure: {photos[0]}")
                print(f"   URL starts with: {photos[0]['url'][:50]}...")

        # Send to Airtable
        headers = {
            'Authorization': f'Bearer {AIRTABLE_API_KEY}',
            'Content-Type': 'application/json'
        }

        url = f'https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}'
        print(f"\n=== Sending request to: {url} ===")

        response = requests.post(url, headers=headers, json=data)

        print(f"\n=== Airtable Response ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        # If there's an error, check if it's related to photos
        if response.status_code != 200 and 'photo' in response.text.lower():
            print("\n⚠️ PHOTO-RELATED ERROR DETECTED!")
            print("This usually means:")
            print(
                "1. The field name 'Inspection Photos' doesn't match your Airtable field")
            print("2. The field exists but is not an Attachment type")
            print("3. Check your Airtable base for the exact field name")

        if response.status_code == 200:
            result_data = response.json()

            # Enhanced success response with photo upload status
            success_msg = f"Item submitted successfully!"
            if inspection_photos:
                success_msg += f" {len(inspection_photos)} inspection photos uploaded."
            elif photo_count > 0:
                success_msg += f" Note: {photo_count} photos selected but not uploaded (check Cloudinary config)."

            return jsonify({
                "success": True,
                "record_id": result_data.get('id'),
                "photos_uploaded": len(inspection_photos) if inspection_photos else 0,
                "message": success_msg
            })
        else:
            # Parse Airtable error response
            error_msg = "Unknown error"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_type = error_data['error'].get(
                        'type', 'Unknown error')
                    error_message = error_data['error'].get('message', '')

                    # Check which field is causing the issue
                    if 'INVALID_VALUE_FOR_COLUMN' in error_type or 'INVALID_ATTACHMENT' in error_type:
                        error_msg = f"{error_type}: {error_message}"

                        # Check if it's the inspection photos field
                        if 'Inspection Photos' in error_message:
                            error_msg += "\n\nPossible issues:\n"
                            error_msg += "1. 'Inspection Photos' field doesn't exist in Airtable\n"
                            error_msg += "2. Field exists but is not an Attachment type\n"
                            error_msg += "3. Field name has different capitalization or spacing\n"
                            error_msg += "\nCheck browser console for available field names."
                    else:
                        error_msg = error_message or error_type

                    print(f"Airtable Error Details: {error_data}")
            except:
                error_msg = response.text

            print(f"Error: {error_msg}")
            return jsonify({"success": False, "error": error_msg})

    except Exception as e:
        print(f"\n=== Exception occurred ===")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})


if __name__ == '__main__':
    print("\n" + "="*60)
    print("4more Inventory Management System")
    print("="*60)

    # Check configuration
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        print("\n⚠️  WARNING: Airtable credentials not configured!")
        print("Create a .env file with:")
        print("  AIRTABLE_API_KEY=your_api_key")
        print("  AIRTABLE_BASE_ID=your_base_id")
        print("  AIRTABLE_TABLE_NAME=Items")
    else:
        print("✓ Airtable configured")

    if CLOUDINARY_AVAILABLE and CLOUDINARY_CLOUD_NAME:
        print("✓ Cloudinary configured - Inspection photos will be uploaded")
    else:
        print("\n📸 To enable inspection photo uploads:")
        print("1. Sign up for free at https://cloudinary.com")
        print("2. Run: pip install cloudinary")
        print("3. Add to your .env file:")
        print("   CLOUDINARY_CLOUD_NAME=your_cloud_name")
        print("   CLOUDINARY_API_KEY=your_api_key")
        print("   CLOUDINARY_API_SECRET=your_api_secret")

    print("\n🚀 Starting server at http://localhost:5000")
    print("\n📋 To diagnose inspection photo issues:")
    print("1. Open http://localhost:5000 in your browser")
    print("2. Open browser console (F12)")
    print("3. Look for 'Available items table fields' to see your actual field names")
    print("4. Or visit these diagnostic URLs:")
    print("   - http://localhost:5000/test-airtable - See all table fields")
    print("   - http://localhost:5000/test-photo-field - Test if photos can be saved")
    print("   - http://localhost:5000/find-attachment-fields - Find attachment fields")
    print("5. Update INSPECTION_PHOTOS_FIELD_NAME in submit() function (~line 1750)")
    print("="*60 + "\n")

    app.run(debug=True, port=5000)
