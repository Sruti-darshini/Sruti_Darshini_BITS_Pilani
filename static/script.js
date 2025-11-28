// Global state
let currentFile = null;
let currentResults = null;

// DOM Elements
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const selectedFile = document.getElementById('selectedFile');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const processBtn = document.getElementById('processBtn');
const cancelBtn = document.getElementById('cancelBtn');
const processing = document.getElementById('processing');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');
const errorMessage = document.getElementById('errorMessage');
const newUploadBtn = document.getElementById('newUploadBtn');
const retryBtn = document.getElementById('retryBtn');
const exportJsonBtn = document.getElementById('exportJsonBtn');
const exportCsvBtn = document.getElementById('exportCsvBtn');

// File Upload Handlers
uploadBox.addEventListener('click', () => fileInput.click());

uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('drag-over');
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.classList.remove('drag-over');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

function handleFileSelect(file) {
    // Validate file type
    const validTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/heic'];
    if (!validTypes.includes(file.type) && !file.name.match(/\.(pdf|jpg|jpeg|png|heic)$/i)) {
        alert('Please select a valid file (PDF, JPEG, PNG, or HEIC)');
        return;
    }

    // Validate file size (10MB limit)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
        alert('File size exceeds 10MB limit');
        return;
    }

    currentFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);

    uploadBox.style.display = 'none';
    selectedFile.style.display = 'block';
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

// Process Button
processBtn.addEventListener('click', async () => {
    if (!currentFile) return;

    // Upload file and get URL (for demo, we'll use a mock URL)
    // In production, you'd upload to a storage service first
    selectedFile.style.display = 'none';
    processing.style.display = 'block';
    errorSection.style.display = 'none';
    resultsSection.style.display = 'none';

    try {
        // Create FormData and upload file
        const formData = new FormData();
        formData.append('file', currentFile);

        // For this demo, we'll use the file upload endpoint
        // You'll need to add this endpoint to your FastAPI app
        const uploadResponse = await fetch('/api/v1/invoices/upload', {
            method: 'POST',
            body: formData
        });

        if (!uploadResponse.ok) {
            throw new Error('Upload failed');
        }

        const result = await uploadResponse.json();

        if (result.is_success) {
            displayResults(result.data);
        } else {
            throw new Error(result.error || 'Processing failed');
        }

    } catch (error) {
        console.error('Error:', error);
        showError(error.message);
    } finally {
        processing.style.display = 'none';
    }
});

// Cancel Button
cancelBtn.addEventListener('click', resetUpload);

function resetUpload() {
    currentFile = null;
    fileInput.value = '';
    uploadBox.style.display = 'block';
    selectedFile.style.display = 'none';
    processing.style.display = 'none';
    errorSection.style.display = 'none';
    resultsSection.style.display = 'none';
}

// Display Results
function displayResults(data) {
    currentResults = data;

    // Calculate total amount from all items
    let totalAmount = 0;
    data.pagewise_line_items.forEach(page => {
        page.bill_items.forEach(item => {
            totalAmount += (item.item_amount || 0);
        });
    });

    // Update summary cards
    document.getElementById('totalItems').textContent = data.total_item_count;
    document.getElementById('reconciledAmount').textContent = '$' + totalAmount.toFixed(2);
    document.getElementById('pagesProcessed').textContent = data.pagewise_line_items.length;

    // Display line items by page
    const container = document.getElementById('lineItemsContainer');
    container.innerHTML = '';

    data.pagewise_line_items.forEach(page => {
        const pageSection = document.createElement('div');
        pageSection.className = 'page-section';

        const pageHeader = document.createElement('div');
        pageHeader.className = 'page-header';
        pageHeader.textContent = `Page ${page.page_no} - ${page.bill_items.length} items`;
        pageSection.appendChild(pageHeader);

        const table = document.createElement('table');
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Item Name</th>
                    <th>Quantity</th>
                    <th>Rate</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
                ${page.bill_items.map(item => `
                    <tr>
                        <td>${item.item_name || 'N/A'}</td>
                        <td>${item.item_quantity || 0}</td>
                        <td>$${(item.item_rate || 0).toFixed(2)}</td>
                        <td class="amount">$${(item.item_amount || 0).toFixed(2)}</td>
                    </tr>
                `).join('')}
            </tbody>
        `;
        pageSection.appendChild(table);
        container.appendChild(pageSection);
    });

    resultsSection.style.display = 'block';
}

// Show Error
function showError(message) {
    errorMessage.textContent = message;
    errorSection.style.display = 'block';
}

// New Upload Button
newUploadBtn.addEventListener('click', resetUpload);

// Retry Button
retryBtn.addEventListener('click', () => {
    errorSection.style.display = 'none';
    selectedFile.style.display = 'block';
});

// Export JSON
exportJsonBtn.addEventListener('click', () => {
    if (!currentResults) return;

    const dataStr = JSON.stringify(currentResults, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'invoice_data.json';
    a.click();
    URL.revokeObjectURL(url);
});

// Export CSV
exportCsvBtn.addEventListener('click', () => {
    if (!currentResults) return;

    let csv = 'Page,Item Name,Quantity,Rate,Amount\n';

    currentResults.pagewise_line_items.forEach(page => {
        page.bill_items.forEach(item => {
            csv += `${page.page_no},"${item.item_name}",${item.item_quantity},${item.item_rate},${item.item_amount}\n`;
        });
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'invoice_data.csv';
    a.click();
    URL.revokeObjectURL(url);
});
