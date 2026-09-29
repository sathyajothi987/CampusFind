// ==========================================
// CampusFind Home Page - Multilingual
// ==========================================

const translations = {

    en: {
        home: "Home",
        about: "About",
        features: "Features",
        contact: "Contact",

        title: "Find What's Lost.<br>Reconnect What Matters.",

        description:
            "CampusFind helps students report, search and recover lost items quickly and securely across campus.",

        search: "🔍 Search Items",
        lost: "📦 Report Lost",
        found: "🎁 Report Found",

        login: "Login",
        register: "Register"
    },


    ta: {
        home: "முகப்பு",
        about: "எங்களை பற்றி",
        features: "வசதிகள்",
        contact: "தொடர்பு",

        title:
            "இழந்ததை கண்டுபிடியுங்கள்.<br>முக்கியமானவற்றை மீண்டும் பெறுங்கள்.",

        description:
            "CampusFind மாணவர்கள் இழந்த பொருட்களை பதிவு செய்து, தேடி, விரைவாகவும் பாதுகாப்பாகவும் மீட்டெடுக்க உதவுகிறது.",

        search: "🔍 தேடு",
        lost: "📦 இழந்த பொருள்",
        found: "🎁 கண்டெடுத்த பொருள்",

        login: "உள்நுழைக",
        register: "பதிவு"
    },


    hi: {
        home: "होम",
        about: "हमारे बारे में",
        features: "सुविधाएँ",
        contact: "संपर्क",

        title:
            "खोई हुई वस्तु खोजें।<br>अपनी महत्वपूर्ण चीज़ें वापस पाएं।",

        description:
            "CampusFind छात्रों को खोई हुई वस्तुओं की रिपोर्ट करने, खोजने और सुरक्षित रूप से वापस पाने में सहायता करता है।",

        search: "🔍 खोजें",
        lost: "📦 खोई वस्तु",
        found: "🎁 मिली हुई वस्तु",

        login: "लॉगिन",
        register: "पंजीकरण"
    }

};


// ==========================================
// CHANGE HOME LANGUAGE
// ==========================================

function changeLanguage() {

    const language =
        document.getElementById("language").value;


    // Save language globally
    saveCampusFindLanguage(language);


    const t =
        translations[language];


    // Navigation

    document.getElementById("nav-home").innerHTML =
        t.home;

    document.getElementById("nav-about").innerHTML =
        t.about;

    document.getElementById("nav-features").innerHTML =
        t.features;

    document.getElementById("nav-contact").innerHTML =
        t.contact;


    // Hero

    document.getElementById("hero-title").innerHTML =
        t.title;

    document.getElementById("hero-description").innerHTML =
        t.description;


    // Buttons

    document.getElementById("search-btn").innerHTML =
        t.search;

    document.getElementById("lost-btn").innerHTML =
        t.lost;

    document.getElementById("found-btn").innerHTML =
        t.found;


    // Login / Register

    const loginButton =
        document.getElementById("login-btn");

    if (loginButton) {

        loginButton.innerHTML =
            t.login;

    }


    const registerButton =
        document.getElementById("register-btn");

    if (registerButton) {

        registerButton.innerHTML =
            t.register;

    }


    // Update HTML language

    document.documentElement.lang =
        language;

}


// ==========================================
// LOAD SAVED LANGUAGE
// ==========================================

document.addEventListener("DOMContentLoaded", function () {

    const savedLanguage =
        getCampusFindLanguage();


    const languageSelect =
        document.getElementById("language");


    if (languageSelect) {

        languageSelect.value =
            savedLanguage;


        // Apply saved language
        changeLanguage();

    }

});