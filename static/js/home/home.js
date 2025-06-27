// =========================
// 📁 home.js - ClinicHub Medical
// Healthcare UI System
// =========================

document.addEventListener('DOMContentLoaded', function () {
  // Initialize animated counters
  initAnimatedCounters();
  
  // Initialize medical cards
  initMedicalCards();
  
  // Initialize AI demo
  initAIDemo();
  
  // Initialize interactive organs
  initOrganPreview();
  
  // Initialize typing animation
  initTypingEffect();
  
  // Initialize mobile menu
  initMobileMenu();
});

function initAnimatedCounters() {
  const counters = document.querySelectorAll('.stat-number');
  const animationDuration = 2000;
  const frameDuration = 1000 / 60;
  const totalFrames = Math.round(animationDuration / frameDuration);
  
  const easeOutQuad = t => t * (2 - t);
  
  const startCounting = (element) => {
    const target = parseInt(element.getAttribute('data-count'));
    const start = 0;
    let frame = 0;
    
    const counter = setInterval(() => {
      frame++;
      
      const progress = easeOutQuad(frame / totalFrames);
      const current = Math.round(target * progress);
      
      element.innerText = current.toLocaleString();
      
      if (frame === totalFrames) clearInterval(counter);
    }, frameDuration);
  };
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        startCounting(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });
  
  counters.forEach(counter => {
    counter.innerText = '0';
    observer.observe(counter);
  });
}

function initMedicalCards() {
  // Add tilt effect to doctor cards
  VanillaTilt.init(document.querySelectorAll('.doctor-card'), {
    max: 5,
    speed: 300,
    scale: 1.03
  });
  
  // Add hover effect to action cards
  const actionCards = document.querySelectorAll('.medical-action');
  
  actionCards.forEach(card => {
    card.addEventListener('mouseenter', () => {
      card.style.transform = 'translateY(-5px)';
      card.style.boxShadow = '0 15px 25px rgba(26, 158, 143, 0.15)';
    });
    
    card.addEventListener('mouseleave', () => {
      card.style.transform = 'translateY(0)';
      card.style.boxShadow = '0 10px 20px rgba(0, 0, 0, 0.08)';
    });
  });
}

function initAIDemo() {
  const processSteps = document.querySelectorAll('.process-step');
  
  // Animate process steps
  let currentStep = 0;
  
  function animateProcess() {
    processSteps.forEach(step => step.classList.remove('active'));
    processSteps[currentStep].classList.add('active');
    
    currentStep = (currentStep + 1) % processSteps.length;
  }
  
  setInterval(animateProcess, 1500);
}

function initOrganPreview() {
  const organs = document.querySelectorAll('.organ');
  let currentIndex = 0;
  
  function activateOrgan(index) {
    organs.forEach(organ => organ.classList.remove('active'));
    organs[index].classList.add('active');
  }
  
  // Cycle through organs
  setInterval(() => {
    currentIndex = (currentIndex + 1) % organs.length;
    activateOrgan(currentIndex);
  }, 3000);
}

function initTypingEffect() {
  const typingElement = document.querySelector('.typing-text');
  const texts = [
    "Management Platform",
    "Diagnostic System",
    "Patient Hub",
    "AI Assistant"
  ];
  
  let textIndex = 0;
  let charIndex = 0;
  let isDeleting = false;
  let typingSpeed = 150;
  
  function type() {
    const currentText = texts[textIndex];
    
    if (isDeleting) {
      typingElement.textContent = currentText.substring(0, charIndex - 1);
      charIndex--;
    } else {
      typingElement.textContent = currentText.substring(0, charIndex + 1);
      charIndex++;
    }
    
    if (!isDeleting && charIndex === currentText.length) {
      isDeleting = true;
      typingSpeed = 100;
      setTimeout(type, 1000);
    } else if (isDeleting && charIndex === 0) {
      isDeleting = false;
      textIndex = (textIndex + 1) % texts.length;
      typingSpeed = 150;
      setTimeout(type, 500);
    } else {
      setTimeout(type, typingSpeed);
    }
  }
  
  setTimeout(type, 1000);
}

function initMobileMenu() {
  const menuToggle = document.querySelector('.mobile-menu-toggle');
  const nav = document.querySelector('.medical-nav-links ul');
  
  menuToggle.addEventListener('click', () => {
    if (nav.style.display === 'flex') {
      nav.style.display = 'none';
      menuToggle.classList.remove('active');
    } else {
      nav.style.display = 'flex';
      menuToggle.classList.add('active');
    }
  });
}