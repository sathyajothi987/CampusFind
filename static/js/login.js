// ==========================================
// CampusFind Login - Multilingual
// ==========================================

const loginTranslations = {

    en: {
        logo: "CampusFind",
        title: "Welcome Back!",
        description: "Login to report, search and recover lost items securely.",
        heading: "Login",
        email: "Email",
        password: "Password",
        login: "Login",
        noAccount: "Don't have an account?",
        register: "Register",
        backHome: "Back to Home"
    },

    ta: {
        logo: "CampusFind",
        title: "மீண்டும் வரவேற்கிறோம்!",
        description: "தொலைந்த பொருட்களைப் புகாரளிக்கவும், தேடவும் மற்றும் பாதுகாப்பாக மீட்டெடுக்கவும் உள்நுழையுங்கள்.",
        heading: "உள்நுழைவு",
        email: "மின்னஞ்சல்",
        password: "கடவுச்சொல்",
        login: "உள்நுழைக",
        noAccount: "கணக்கு இல்லையா?",
        register: "பதிவு செய்யவும்",
        backHome: "முகப்புக்குத் திரும்பு"
    },

    hi: {
        logo: "CampusFind",
        title: "वापसी पर स्वागत है!",
        description: "खोई हुई वस्तुओं की रिपोर्ट करने, खोजने और सुरक्षित रूप से वापस पाने के लिए लॉगिन करें।",
        heading: "लॉगिन",
        email: "ईमेल",
        password: "पासवर्ड",
        login: "लॉगिन",
        noAccount: "क्या आपका खाता नहीं है?",
        register: "रजिस्टर करें",
        backHome: "होम पर वापस जाएँ"
    }

};


// ==========================================
// CHANGE LOGIN LANGUAGE
// ==========================================

function changeLoginLanguage() {

    const language =
        document.getElementById("language").value;

    const t =
        loginTranslations[language];


    document.getElementById("logo-text").textContent =
        t.logo;

    document.getElementById("login-title").textContent =
        t.title;

    document.getElementById("login-description").textContent =
        t.description;

    document.getElementById("login-heading").textContent =
        t.heading;

    document.getElementById("email").placeholder =
        t.email;

    document.getElementById("password").placeholder =
        t.password;

    document.getElementById("login-button-text").textContent =
        t.login;

    document.getElementById("no-account").textContent =
        t.noAccount;

    document.getElementById("register-link").textContent =
        t.register;

    document.getElementById("back-home-text").textContent =
        t.backHome;


    // Update browser language
    document.documentElement.lang =
        language;


    // Save selected language
    saveCampusFindLanguage(language);
}


// ==========================================
// LOAD LANGUAGE FROM HOME
// ==========================================

document.addEventListener("DOMContentLoaded", function () {

    const savedLanguage =
        getCampusFindLanguage();

    const languageSelect =
        document.getElementById("language");


    if (languageSelect) {

        languageSelect.value =
            savedLanguage;

        changeLoginLanguage();

    }

});