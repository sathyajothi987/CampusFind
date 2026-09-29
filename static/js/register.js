// ================= REGISTER LANGUAGE =================

const registerTranslations = {

    en: {
        logo: "CampusFind",
        title: "Create Your Account",
        description: "Join CampusFind and help your campus community report, search and recover lost items quickly.",
        heading: "Create Account",
        name: "Full Name",
        email: "Email",
        password: "Password",
        confirmPassword: "Confirm Password",
        register: "Create Account",
        alreadyAccount: "Already have an account?",
        login: "Login",
        backHome: "Back to Home"
    },

    ta: {
        logo: "CampusFind",
        title: "உங்கள் கணக்கை உருவாக்குங்கள்",
        description: "CampusFind-ல் இணைந்து, உங்கள் வளாக சமூகத்திற்கு தொலைந்த பொருட்களைப் புகாரளிக்கவும், தேடவும் மற்றும் விரைவாக மீட்டெடுக்கவும் உதவுங்கள்.",
        heading: "கணக்கை உருவாக்கவும்",
        name: "முழு பெயர்",
        email: "மின்னஞ்சல்",
        password: "கடவுச்சொல்",
        confirmPassword: "கடவுச்சொல்லை உறுதிப்படுத்தவும்",
        register: "கணக்கை உருவாக்கவும்",
        alreadyAccount: "ஏற்கனவே கணக்கு உள்ளதா?",
        login: "உள்நுழைக",
        backHome: "முகப்புக்குத் திரும்பு"
    },

    hi: {
        logo: "CampusFind",
        title: "अपना खाता बनाएँ",
        description: "CampusFind से जुड़ें और अपने कैंपस समुदाय को खोई हुई वस्तुओं की रिपोर्ट करने, खोजने और जल्दी वापस पाने में मदद करें।",
        heading: "खाता बनाएँ",
        name: "पूरा नाम",
        email: "ईमेल",
        password: "पासवर्ड",
        confirmPassword: "पासवर्ड की पुष्टि करें",
        register: "खाता बनाएँ",
        alreadyAccount: "क्या आपका पहले से खाता है?",
        login: "लॉगिन",
        backHome: "होम पर वापस जाएँ"
    }

};


// ================= CHANGE LANGUAGE =================

function changeRegisterLanguage() {

    const language =
        document.getElementById("language").value;

    const t =
        registerTranslations[language];


    document.getElementById("logo-text").textContent =
        t.logo;


    document.getElementById("register-title").textContent =
        t.title;


    document.getElementById("register-description").textContent =
        t.description;


    document.getElementById("register-heading").textContent =
        t.heading;


    document.getElementById("name").placeholder =
        t.name;


    document.getElementById("email").placeholder =
        t.email;


    document.getElementById("password").placeholder =
        t.password;


    document.getElementById("confirm-password").placeholder =
        t.confirmPassword;


    document.getElementById("register-button-text").textContent =
        t.register;


    document.getElementById("already-account").textContent =
        t.alreadyAccount;


    document.getElementById("login-link-text").textContent =
        t.login;


    document.getElementById("back-home-text").textContent =
        t.backHome;


    document.documentElement.lang =
        language;


    localStorage.setItem(
        "campusFindLanguage",
        language
    );
}


// ================= LOAD SAVED LANGUAGE =================

document.addEventListener("DOMContentLoaded", function () {

    const savedLanguage =
        localStorage.getItem("campusFindLanguage") || "en";


    const languageSelect =
        document.getElementById("language");


    if (languageSelect) {

        languageSelect.value =
            savedLanguage;

        changeRegisterLanguage();

    }

});