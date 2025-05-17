// --- Utility Functions ---
function showMessage(message, isError = false) {
    alert(message); // Replace with a more user-friendly display if needed
}

function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function showPaymentForm(itemName, amount, paymentMethod) {
  const modal = document.getElementById('payment-modal');
  const itemNameInput = document.getElementById('item-name');
  const amountInput = document.getElementById('amount');
  const paymentMethodInput = document.getElementById('payment-method');

  if (modal && itemNameInput && amountInput && paymentMethodInput) {
    itemNameInput.value = itemName;
    amountInput.value = amount;
    paymentMethodInput.value = paymentMethod;

    modal.style.display = 'block';
  }
}

function closePaymentModal() {
  const modal = document.getElementById('payment-modal');
  if (modal) {
    modal.style.display = 'none';
  }
}

function handlePurposeChange(select) {
  const prQuestions = document.getElementById('pr-questions');
  if (select.value === 'pr') {
    prQuestions.style.display = 'block';
  } else {
    prQuestions.style.display = 'none';
  }
}


// --- The rest of your script.js code (unchanged) ---

document.addEventListener('DOMContentLoaded', function () {
    // --- Preloader ---
    const preloader = document.querySelector('.preloader');
    if (preloader) {
        window.addEventListener('load', () => {
            preloader.classList.add('loaded');
        });
    }

    // --- Mobile Navigation (Burger Menu) ---
    const burger = document.querySelector('.burger');
    const navLinks = document.querySelector('.nav-links');

    if (burger && navLinks) {
        burger.addEventListener('click', () => {
            navLinks.classList.toggle('nav-active');
            burger.classList.toggle('toggle');
        });
    }

    // --- Modal Popup ---
    const modal = document.getElementById('demoModal');
    const closeButton = document.querySelector('.close-button');
    const demoForm = document.getElementById('demo-form');
    const formMessage = document.getElementById('form-message');

    function openModal() {
        if (modal) {
            modal.style.display = 'flex';
            const firstInput = modal.querySelector('input');
            if (firstInput) {
                firstInput.focus();
            }
        }
    }

    setTimeout(openModal, 10000); // Open the modal after 2 seconds

    function closeModal() {
        if (modal) {
            modal.style.display = 'none';
        }
    }

    if (closeButton) {
        closeButton.addEventListener('click', closeModal);
    }

    window.addEventListener('click', (event) => {
        if (event.target == modal) {
            closeModal();
        }
    });

    if (demoForm) {
        demoForm.addEventListener('submit', function (event) {
            event.preventDefault();

            // 1. Static WhatsApp Message
            const whatsappMessage = "Hi, I am interested in this please let me know more details";

            // 2. Encode the message
            const encodedMessage = encodeURIComponent(whatsappMessage);

            // 3. Construct the WhatsApp URL
            const whatsappNumber = "+13653062049"; // ***REPLACE THIS***
            const whatsappUrl = `https://wa.me/<span class="math-inline">\{whatsappNumber\}?text\=</span>{encodedMessage}`;

            // 4. Log the URL for debugging
            console.log("WhatsApp URL:", whatsappUrl);

            // 5. Redirect to WhatsApp
            window.location.href = whatsappUrl;
        });
    }

    // --- Button Click Animation ---
    const ctaButtons = document.querySelectorAll('.cta-button');
    ctaButtons.forEach(button => {
        button.addEventListener('click', function () {
            this.classList.add('clicked');
            setTimeout(() => {
                this.classList.remove('clicked');
            }, 800);
        });
    });

    // --- Scroll-Triggered Animations (Intersection Observer) ---

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible'); // Add a class when in view
            } else {
                // Optional: Remove the class if you want the animation to only happen once
                // entry.target.classList.remove('is-visible');
            }
        });
    }, {
        threshold: 0.1 // Element is considered "in view" when 10% is visible
    });

    // Observe elements with the 'animate-on-scroll' class
    const elementsToAnimate = document.querySelectorAll('.animate-on-scroll');
    elementsToAnimate.forEach(element => {
        observer.observe(element);
    });

    // --- Logo Animation (Subtle) ---
    const logo = document.querySelector('.logo a');
    if (logo) {
        logo.addEventListener('mouseover', () => {
            logo.classList.add('logo-hover');
        });
        logo.addEventListener('mouseout', () => {
            logo.classList.remove('logo-hover');
        });
    }
    // --- Sticky Header Animation ---
    let lastScrollTop = 0;
    const header = document.querySelector('header'); // Select the header

    window.addEventListener('scroll', () => {
        let currentScroll = window.pageYOffset || document.documentElement.scrollTop;

        if (currentScroll > lastScrollTop) {
            // Scrolling Down
            header.style.transform = 'translateY(-100%)';
        } else {
            // Scrolling Up
            header.style.transform = 'translateY(0)';
        }
        lastScrollTop = currentScroll <= 0 ? 0 : currentScroll;
    }, false);
});
