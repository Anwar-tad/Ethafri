// EthAfri/static/js/global.js

document.addEventListener("DOMContentLoaded", function() {
    console.log("EthAfri Smart System Initialized.");

    // የቋንቋ መቀያየሪያ ሲነካ የሚሰራ ራስ-ሰር አኒሜሽን ወይም ሎደር ማሳያ
    const langSelect = document.querySelector('select[name="language"]');
    if (langSelect) {
        langSelect.addEventListener("change", function() {
            // ገጹ እስኪቀየር የፓነል ሎደር ማሳየት ይቻላል
            document.body.style.opacity = "0.6";
            document.body.style.transition = "opacity 0.3s ease";
        });
    }

    // የሞባይል ቦተም ናቭ ሲነካ አዝራሩን ጎልቶ እንዲታይ (Active) ማድረግ
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll(".bottom-nav a");
    navLinks.forEach(link => {
        const linkPath = link.getAttribute("href");
        if (linkPath === currentPath) {
            link.style.color = "var(--primary-color)";
            const icon = link.querySelector("i");
            if (icon) icon.style.transform = "scale(1.1)";
        }
    });
});
