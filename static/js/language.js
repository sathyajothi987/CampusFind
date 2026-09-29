// ==========================================
// CampusFind - Common Language System
// ==========================================

const CAMPUSFIND_LANGUAGE_KEY = "campusFindLanguage";


// Get currently selected language
function getCampusFindLanguage() {

    return localStorage.getItem(CAMPUSFIND_LANGUAGE_KEY) || "en";

}


// Save selected language
function saveCampusFindLanguage(language) {

    localStorage.setItem(
        CAMPUSFIND_LANGUAGE_KEY,
        language
    );

}


// Set the language selector to saved language
function setSavedLanguage() {

    const languageSelect =
        document.getElementById("language");

    if (languageSelect) {

        languageSelect.value =
            getCampusFindLanguage();

    }

}


// Save language whenever selector changes
function saveSelectedLanguage() {

    const languageSelect =
        document.getElementById("language");

    if (languageSelect) {

        saveCampusFindLanguage(
            languageSelect.value
        );

    }

}


// Run when page loads
document.addEventListener("DOMContentLoaded", function () {

    setSavedLanguage();

});