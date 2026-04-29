document.addEventListener('DOMContentLoaded', () => {
    // 1. Scroll-triggered CTA Logic
    const scrollCta = document.getElementById('scrollCta');

    // Function to calculate scroll percentage and toggle CTA visibility
    const handleScroll = () => {
        const scrollTop = window.scrollY || document.documentElement.scrollTop;
        const scrollHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const scrollPercentage = (scrollTop / scrollHeight) * 100;

        if (scrollPercentage >= 70) {
            scrollCta.classList.add('is-visible');
        } else {
            scrollCta.classList.remove('is-visible');
        }
    };

    // Initial check in case user loads page already scrolled down
    handleScroll();

    // Add event listener with a small passive indication for performance
    window.addEventListener('scroll', handleScroll, { passive: true });

    // 2. Intersection Observer for fade-in animations
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.15
    };

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                // Optional: Stop observing once it has become visible
                // observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    const fadeElements = document.querySelectorAll('.fade-in-section');
    fadeElements.forEach(el => observer.observe(el));
});
