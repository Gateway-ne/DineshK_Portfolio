/* ==========================================================================
   Dinesh K - PLM / Teamcenter Developer Portfolio Script
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const header = document.getElementById('header');
  const themeToggle = document.getElementById('theme-toggle');
  const mobileToggle = document.getElementById('mobile-toggle');
  const navMenu = document.getElementById('nav-menu');
  const navLinks = document.querySelectorAll('.nav-link');
  const currentYearSpan = document.getElementById('current-year');
  const typingTarget = document.getElementById('typing-target');
  
  // Set current year in footer
  if (currentYearSpan) {
    currentYearSpan.textContent = new Date().getFullYear();
  }

  // Calculate & auto-update total years of experience dynamically (Start: Feb 2024)
  const expStartDate = new Date(2024, 1, 1); // February 2024
  const currentDate = new Date();
  const diffYears = (currentDate - expStartDate) / (1000 * 60 * 60 * 24 * 365.25);
  const formattedExpYears = (diffYears > 0 ? diffYears.toFixed(1) : '2.3') + '+';

  document.querySelectorAll('.exp-years-dynamic').forEach(el => {
    el.textContent = formattedExpYears;
  });

  // ==========================================================================
  // 1. Dark / Light Theme Toggle
  // ==========================================================================
  const savedTheme = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);

  themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Rotate button icon for visual feedback
    const svg = themeToggle.querySelector('svg');
    if (svg) {
      svg.style.transform = svg.style.transform === 'rotate(360deg)' ? 'rotate(0deg)' : 'rotate(360deg)';
    }
  });

  // ==========================================================================
  // 2. Typing Effect (Hero Section)
  // ==========================================================================
  const words = ['PLM Developer', 'Teamcenter Developer', 'System Engineer', 'ITK & SOA Customizer'];
  let wordIndex = 0;
  let charIndex = 0;
  let isDeleting = false;
  let typingSpeed = 100;

  function type() {
    const currentWord = words[wordIndex];
    
    if (isDeleting) {
      // Deleting character
      typingTarget.textContent = currentWord.substring(0, charIndex - 1);
      charIndex--;
      typingSpeed = 50; // Speed up deletion
    } else {
      // Typing character
      typingTarget.textContent = currentWord.substring(0, charIndex + 1);
      charIndex++;
      typingSpeed = 120; // Normal typing speed
    }

    if (!isDeleting && charIndex === currentWord.length) {
      // Pause at full word
      typingSpeed = 1500;
      isDeleting = true;
    } else if (isDeleting && charIndex === 0) {
      isDeleting = false;
      // Move to next word
      wordIndex = (wordIndex + 1) % words.length;
      typingSpeed = 500; // Pause before typing next word
    }

    setTimeout(type, typingSpeed);
  }

  if (typingTarget) {
    type();
  }

  // ==========================================================================
  // 3. Header Scroll Behavior & Sticky Navigation
  // ==========================================================================
  window.addEventListener('scroll', () => {
    if (window.scrollY > 50) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
    
    highlightActiveNavLink();
  });

  function highlightActiveNavLink() {
    const scrollPosition = window.scrollY + 120; // Offset for header height
    
    document.querySelectorAll('section').forEach(section => {
      const sectionTop = section.offsetTop;
      const sectionHeight = section.offsetHeight;
      const sectionId = section.getAttribute('id');
      
      if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
        navLinks.forEach(link => {
          link.classList.remove('active');
          if (link.getAttribute('href') === `#${sectionId}`) {
            link.classList.add('active');
          }
        });
      }
    });
  }

  // ==========================================================================
  // 4. Mobile Navigation Menu Toggle
  // ==========================================================================
  mobileToggle.addEventListener('click', () => {
    mobileToggle.classList.toggle('open');
    navMenu.classList.toggle('open');
  });

  // Close mobile nav when clicking a link
  navLinks.forEach(link => {
    link.addEventListener('click', () => {
      mobileToggle.classList.remove('open');
      navMenu.classList.remove('open');
    });
  });

  // ==========================================================================
  // 5. Skills Section Tabs Control
  // ==========================================================================
  const skillTabs = document.querySelectorAll('.skills-nav-btn');
  const skillPanes = document.querySelectorAll('.skills-pane');

  skillTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      // Remove active from all tabs & panes
      skillTabs.forEach(t => t.classList.remove('active'));
      skillPanes.forEach(p => p.classList.remove('active'));

      // Add active to current tab
      tab.classList.add('active');
      
      // Add active to targeted pane
      const targetId = tab.getAttribute('data-target');
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add('active');
      }
    });
  });

  // ==========================================================================
  // 6. Experience Timeline Categories Filter
  // ==========================================================================
  const filterBtns = document.querySelectorAll('.filter-btn');
  const timelineItems = document.querySelectorAll('.timeline-item');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      // Toggle active status
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filterValue = btn.getAttribute('data-filter');

      timelineItems.forEach(item => {
        const itemCategories = item.getAttribute('data-categories').split(' ');
        
        if (filterValue === 'all' || itemCategories.includes(filterValue) || 
            (filterValue === 'lead' && item.querySelector('.timeline-meta').textContent.includes('Lead'))) {
          item.style.display = 'block';
          // Force a reflow/repaint to trigger entry animation
          void item.offsetHeight;
          item.classList.add('visible');
        } else {
          item.classList.remove('visible');
          // Wait for fadeout animation before hiding
          setTimeout(() => {
            if (!item.classList.contains('visible')) {
              item.style.display = 'none';
            }
          }, 300);
        }
      });
    });
  });

  // ==========================================================================
  // 7. Scroll Reveal Timeline Items & Language Bars
  // ==========================================================================
  const revealItems = () => {
    const triggerBottom = window.innerHeight * 0.85;

    // Timeline items scroll reveal
    timelineItems.forEach(item => {
      const itemTop = item.getBoundingClientRect().top;
      if (itemTop < triggerBottom && item.style.display !== 'none') {
        item.classList.add('visible');
      }
    });

    // Language bars animation trigger
    const langSection = document.getElementById('personal');
    if (langSection) {
      const sectionTop = langSection.getBoundingClientRect().top;
      if (sectionTop < triggerBottom) {
        document.querySelectorAll('.lang-fill').forEach(bar => {
          const targetWidth = bar.getAttribute('data-width');
          bar.style.width = targetWidth;
        });
      }
    }
  };

  window.addEventListener('scroll', revealItems);
  revealItems(); // Initial check on load

  // ==========================================================================
  // 8. Japanese Interactive Card Easter Egg
  // ==========================================================================
  const jpPhrases = [
    { jp: '日本語', romaji: 'Nihongo', translation: 'Japanese (Language)' },
    { jp: 'こんにちは', romaji: 'Konnichiwa', translation: 'Hello / Good Afternoon' },
    { jp: 'ありがとう', romaji: 'Arigatou', translation: 'Thank you' },
    { jp: 'はじめまして', romaji: 'Hajimemashite', translation: 'Nice to meet you' },
    { jp: 'がんばります', romaji: 'Ganbarimasu', translation: "I'll do my best" },
    { jp: 'よろしく', romaji: 'Yoroshiku', translation: 'Please favor me / Let\'s work well together' }
  ];

  let jpIndex = 0;
  const jpCard = document.getElementById('jp-interactive-card');
  const jpChar = document.getElementById('jp-char');
  const jpTitle = document.getElementById('jp-title');
  const jpTranslation = document.getElementById('jp-translation');

  if (jpCard) {
    jpCard.addEventListener('click', () => {
      // Increment index
      jpIndex = (jpIndex + 1) % jpPhrases.length;
      const phrase = jpPhrases[jpIndex];

      // Add a quick visual flash/fade transition
      jpChar.style.opacity = 0;
      jpTitle.style.opacity = 0;
      jpTranslation.style.opacity = 0;

      setTimeout(() => {
        jpChar.textContent = phrase.jp;
        jpTitle.textContent = `Romaji: "${phrase.romaji}"`;
        jpTranslation.textContent = `Meaning: ${phrase.translation}`;

        jpChar.style.opacity = 1;
        jpTitle.style.opacity = 1;
        jpTranslation.style.opacity = 1;
      }, 150);
    });

    // CSS styling for transitions
    jpChar.style.transition = 'opacity 0.15s ease-in-out';
    jpTitle.style.transition = 'opacity 0.15s ease-in-out';
    jpTranslation.style.transition = 'opacity 0.15s ease-in-out';
  }

  // ==========================================================================
  // 9. Contact Form Simulation Handler
  // ==========================================================================
  const contactForm = document.getElementById('contact-form');
  const modalAlert = document.getElementById('modal-alert');

  if (contactForm && modalAlert) {
    contactForm.addEventListener('submit', (e) => {
      e.preventDefault(); // Stop standard redirect page refresh
      
      const name = document.getElementById('name').value;
      const email = document.getElementById('email').value;
      const subject = document.getElementById('subject').value;
      const message = document.getElementById('message').value;
      
      // Construct mailto link to open user's email client
      const mailtoLink = `mailto:dineshk.plmdev@gmail.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(`Name: ${name}\nEmail: ${email}\n\nMessage:\n${message}`)}`;
      
      // Open email client
      window.location.href = mailtoLink;
      
      // Show confirmation modal
      modalAlert.classList.add('show');
      
      // Clear values
      contactForm.reset();
      
      // Auto-hide alert notification modal after 4 seconds
      setTimeout(() => {
        modalAlert.classList.remove('show');
      }, 4000);
    });
  }

  // ==========================================================================
  // 10. Certificate Modal Control Handler
  // ==========================================================================
  const certCards = document.querySelectorAll('.cert-card');
  const certModal = document.getElementById('cert-modal');
  const certModalClose = document.getElementById('cert-modal-close');
  const certModalBackdrop = document.getElementById('cert-modal-backdrop');
  
  const certFrame = document.getElementById('cert-frame');
  const certImg = document.getElementById('cert-img');
  const certPlaceholder = document.getElementById('cert-placeholder');
  const targetFilenameSpan = document.getElementById('target-filename');

  const certFileMap = {
    'Teamcenter X Associate Certificate': 'teamcenter-x.pdf',
    'Partner - Service Lifecycle Management (SLM) for Active Workspace 6.3': 'service-lifecycle.png',
    'Mendix Rapid Developer': 'mendix-rapid-developer.png',
    'Azure AI Engineer Associate (AI-102)': 'azure-ai-engineer.jpg',
    'Implement Load Balancing on Compute Engine': 'google-cloud-skills.pdf',
    'Ethical Hacking Certificate': 'ethical-hacking.pdf',
    'Network Security Certification': 'network-security.pdf',
    'Internet of Things (IoT) Certificate': 'iot.pdf'
  };

  certCards.forEach(card => {
    card.addEventListener('click', () => {
      // Check if card has a custom external link (like a Credly badge)
      const externalLink = card.getAttribute('data-link');
      if (externalLink) {
        window.open(externalLink, '_blank');
        return;
      }

      const title = card.querySelector('h4').textContent.trim();
      const filename = certFileMap[title] || 'certificate.pdf';
      const fileUrl = `assets/${filename}`;

      // Reset displays
      certFrame.style.display = 'none';
      certImg.style.display = 'none';
      certPlaceholder.style.display = 'none';
      
      // Update target name in placeholder
      targetFilenameSpan.textContent = filename;

      // Check if file exists by making a HEAD request
      fetch(fileUrl, { method: 'HEAD' })
        .then(response => {
          if (response.ok) {
            // File exists! Load it.
            const fileExtension = filename.split('.').pop().toLowerCase();
            if (fileExtension === 'pdf') {
              certFrame.src = fileUrl;
              certFrame.style.display = 'block';
            } else {
              certImg.src = fileUrl;
              certImg.style.display = 'block';
            }
          } else {
            // File not found (404). Show placeholder guide.
            certPlaceholder.style.display = 'flex';
          }
        })
        .catch(() => {
          // Network error or local file scheme restriction. Fallback to placeholder.
          certPlaceholder.style.display = 'flex';
        });

      // Show modal
      certModal.classList.add('show');
      document.body.style.overflow = 'hidden'; // Block scroll
    });
  });

  const closeCertModal = () => {
    certModal.classList.remove('show');
    // Clear iframe src to stop PDF running in background
    certFrame.src = '';
    document.body.style.overflow = ''; // Restore scroll
  };

  if (certModalClose && certModalBackdrop) {
    certModalClose.addEventListener('click', closeCertModal);
    certModalBackdrop.addEventListener('click', closeCertModal);
  }
});
