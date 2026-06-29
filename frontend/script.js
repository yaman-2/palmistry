// Replace with actual WhatsApp Number (include country code, no '+')
const WHATSAPP_NUMBER = "919997754141"; 

function selectPath(path) {
    document.querySelectorAll('.screen').forEach(el => {
        el.classList.remove('active');
    });
    document.getElementById(`${path}-screen`).classList.add('active');
}

function goBack() {
    document.querySelectorAll('.screen').forEach(el => {
        el.classList.remove('active');
    });
    document.getElementById('selection-screen').classList.add('active');
}

function submitAstrology(e) {
    e.preventDefault();
    
    const name = document.getElementById('astro-name').value;
    const mobile = document.getElementById('astro-mobile').value;
    const email = document.getElementById('astro-email').value;
    const dob = document.getElementById('astro-dob').value;
    const time = document.getElementById('astro-time').value;
    const place = document.getElementById('astro-place').value;

    const message = `*New Astrology Inquiry* 🌟\n\n` +
                    `*Name:* ${name}\n` +
                    `*Mobile:* ${mobile}\n` +
                    `*Email:* ${email}\n` +
                    `*DOB:* ${dob}\n` +
                    `*Time of Birth:* ${time}\n` +
                    `*Place of Birth:* ${place}\n\n` +
                    `Please let me know the next steps.`;

    redirectToWhatsApp(message);
}

function submitPalmistry(e) {
    e.preventDefault();
    
    const name = document.getElementById('palm-name').value;
    const mobile = document.getElementById('palm-mobile').value;
    const email = document.getElementById('palm-email').value;
    const hand = document.getElementById('palm-hand').value;

    const message = `*New Palmistry Inquiry* ✋\n\n` +
                    `*Name:* ${name}\n` +
                    `*Mobile:* ${mobile}\n` +
                    `*Email:* ${email}\n` +
                    `*Handedness:* ${hand}\n\n` +
                    `I will be sending 4-5 images of my palms shortly. Please review them.`;

    redirectToWhatsApp(message);
}

function redirectToWhatsApp(text) {
    const encodedText = encodeURIComponent(text);
    const whatsappUrl = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodedText}`;
    window.open(whatsappUrl, '_blank');
}
