document.addEventListener('DOMContentLoaded', () => {
    const scanBtn = document.getElementById('scanBtn');
    const scanBtnText = document.getElementById('scanBtnText');
    const spinner = document.getElementById('spinner');
    const imageInput = document.getElementById('imageInput');
    
    const mainView = document.getElementById('mainView');
    const resultsView = document.getElementById('resultsView');
    const readingContent = document.getElementById('readingContent');
    const resetBtn = document.getElementById('resetBtn');
    const logoTitle = document.getElementById('logoTitle');

    // Trigger file picker when Scan button is clicked
    scanBtn.addEventListener('click', () => {
        imageInput.click();
    });

    // Handle file selection and API call
    imageInput.addEventListener('change', async (e) => {
        if (!e.target.files.length) return;
        
        const file = e.target.files[0];
        if (!file.type.startsWith('image/')) {
            alert('Please select a valid image file.');
            return;
        }

        // Show loading state
        scanBtnText.style.opacity = '0';
        spinner.style.display = 'block';
        scanBtn.disabled = true;

        const formData = new FormData();
        formData.append('image_file', file);

        try {
            const response = await fetch('/process_palm', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to process image');
            }

            const data = await response.json();
            
            // Switch views
            mainView.classList.add('hidden');
            mainView.classList.remove('flex');
            
            resultsView.classList.remove('hidden');
            resultsView.classList.add('flex');
            
            // Format and display reading
            readingContent.innerHTML = data.reading.replace(/\n/g, '<br><br>');
            
        } catch (error) {
            alert('Cosmic Connection Failed: ' + error.message);
        } finally {
            // Restore button state
            scanBtnText.style.opacity = '1';
            spinner.style.display = 'none';
            scanBtn.disabled = false;
            // Clear input so same file can be selected again if needed
            imageInput.value = '';
        }
    });

    // Reset back to main view
    const resetApp = () => {
        resultsView.classList.add('hidden');
        resultsView.classList.remove('flex');
        
        mainView.classList.remove('hidden');
        mainView.classList.add('flex');
        
        readingContent.innerHTML = '';
    };

    resetBtn.addEventListener('click', resetApp);
    logoTitle.addEventListener('click', resetApp); // Clicking logo resets app
});
