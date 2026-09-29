// ==================================================
// CAMPUSFIND SEARCH JAVASCRIPT
// ==================================================

let lastSearchResults = [];


// ==================================================
// SEARCH PAGE TRANSLATIONS
// ==================================================

const searchTranslations = {

    en: {
        searchTitle: "Search Items",
        searchDescription:
            "Find lost and found items across your campus.",

        searchItemLabel: "Search Item",
        searchPlaceholder: "Enter item name...",

        categoryLabel: "Category",
        locationLabel: "Location",
        statusLabel: "Status",

        searchButton: "Search",

        resultsTitle: "Search Results",
        resultsDescription:
            "Browse reported lost and found items.",

        itemsFound: "items",

        emptyTitle: "No items found",
        emptyDescription:
            "Try changing your search filters.",

        viewDetails: "View Details",

        lost: "Lost",
        found: "Found",

        reportedOn: "Reported on",

        allLocations: "All Locations",
        allStatus: "Lost & Found",
        lostItems: "Lost Items",
        foundItems: "Found Items"
    },

    ta: {
        searchTitle: "பொருட்களை தேடுங்கள்",
        searchDescription:
            "உங்கள் வளாகத்தில் இழந்த மற்றும் கண்டெடுத்த பொருட்களை தேடுங்கள்.",

        searchItemLabel: "பொருளை தேடுங்கள்",
        searchPlaceholder: "பொருளின் பெயரை உள்ளிடுங்கள்...",

        categoryLabel: "வகை",
        locationLabel: "இடம்",
        statusLabel: "நிலை",

        searchButton: "தேடு",

        resultsTitle: "தேடல் முடிவுகள்",
        resultsDescription:
            "பதிவு செய்யப்பட்ட இழந்த மற்றும் கண்டெடுத்த பொருட்களை பார்க்கவும்.",

        itemsFound: "பொருட்கள்",

        emptyTitle: "பொருட்கள் எதுவும் கிடைக்கவில்லை",
        emptyDescription:
            "உங்கள் தேடல் வடிகட்டிகளை மாற்றி முயற்சிக்கவும்.",

        viewDetails: "விவரங்களை பார்க்கவும்",

        lost: "இழந்தது",
        found: "கண்டெடுக்கப்பட்டது",

        reportedOn: "பதிவு செய்த தேதி",

        allLocations: "அனைத்து இடங்கள்",
        allStatus: "இழந்தது & கண்டெடுத்தது",
        lostItems: "இழந்த பொருட்கள்",
        foundItems: "கண்டெடுத்த பொருட்கள்"
    },

    hi: {
        searchTitle: "वस्तुएँ खोजें",
        searchDescription:
            "अपने कैंपस में खोई और मिली हुई वस्तुओं को खोजें।",

        searchItemLabel: "वस्तु खोजें",
        searchPlaceholder: "वस्तु का नाम दर्ज करें...",

        categoryLabel: "श्रेणी",
        locationLabel: "स्थान",
        statusLabel: "स्थिति",

        searchButton: "खोजें",

        resultsTitle: "खोज परिणाम",
        resultsDescription:
            "रिपोर्ट की गई खोई और मिली हुई वस्तुओं को देखें।",

        itemsFound: "वस्तुएँ",

        emptyTitle: "कोई वस्तु नहीं मिली",
        emptyDescription:
            "अपने खोज फ़िल्टर बदलकर फिर से प्रयास करें।",

        viewDetails: "विवरण देखें",

        lost: "खोया हुआ",
        found: "मिला हुआ",

        reportedOn: "रिपोर्ट की तारीख",

        allLocations: "सभी स्थान",
        allStatus: "खोया और मिला",
        lostItems: "खोई हुई वस्तुएँ",
        foundItems: "मिली हुई वस्तुएँ"
    }
};


// ==================================================
// CHANGE SEARCH LANGUAGE
// ==================================================

function changeSearchLanguage() {

    const languageSelect =
        document.getElementById("language");

    if (!languageSelect) {
        return;
    }

    const language = languageSelect.value;

    localStorage.setItem(
        "campusFindLanguage",
        language
    );

    applySearchLanguage(language);
}


// ==================================================
// APPLY SEARCH LANGUAGE
// ==================================================

function applySearchLanguage(language) {

    if (!searchTranslations[language]) {
        language = "en";
    }

    const t = searchTranslations[language];

    const elements = {

        "search-title": t.searchTitle,
        "search-description": t.searchDescription,

        "search-item-label": t.searchItemLabel,
        "category-label": t.categoryLabel,
        "location-label": t.locationLabel,
        "status-label": t.statusLabel,

        "search-button-text": t.searchButton,

        "results-title": t.resultsTitle,
        "results-description": t.resultsDescription,

        "empty-results-title": t.emptyTitle,
        "empty-results-text": t.emptyDescription
    };

    Object.keys(elements).forEach(function(id) {

        const element =
            document.getElementById(id);

        if (element) {
            element.textContent = elements[id];
        }
    });


    const searchInput =
        document.getElementById("search-input");

    if (searchInput) {
        searchInput.placeholder =
            t.searchPlaceholder;
    }


    const locationSelect =
        document.getElementById("location");

    if (locationSelect) {

        const firstOption =
            locationSelect.querySelector(
                'option[value=""]'
            );

        if (firstOption) {
            firstOption.textContent =
                t.allLocations;
        }
    }


    const statusSelect =
        document.getElementById("status");

    if (statusSelect) {

        const allStatusOption =
            statusSelect.querySelector(
                'option[value=""]'
            );

        if (allStatusOption) {
            allStatusOption.textContent =
                t.allStatus;
        }

        const lostOption =
            statusSelect.querySelector(
                'option[value="Lost"]'
            );

        if (lostOption) {
            lostOption.textContent =
                t.lostItems;
        }

        const foundOption =
            statusSelect.querySelector(
                'option[value="Found"]'
            );

        if (foundOption) {
            foundOption.textContent =
                t.foundItems;
        }
    }


    // Update existing results if available
    if (lastSearchResults.length > 0) {
        displaySearchResults(
            lastSearchResults,
            language
        );
    }
}


// ==================================================
// SEARCH ITEMS
// ==================================================

async function searchItems() {

    const searchInput =
        document.getElementById("search-input");

    const category =
        document.getElementById("category");

    const location =
        document.getElementById("location");

    const status =
        document.getElementById("status");


    const itemValue =
        searchInput
            ? searchInput.value.trim()
            : "";

    const categoryValue =
        category
            ? category.value
            : "";

    const locationValue =
        location
            ? location.value
            : "";

    const statusValue =
        status
            ? status.value
            : "";


    const parameters =
        new URLSearchParams();


    if (itemValue) {
        parameters.append(
            "item",
            itemValue
        );
    }

    if (categoryValue) {
        parameters.append(
            "category",
            categoryValue
        );
    }

    if (locationValue) {
        parameters.append(
            "location",
            locationValue
        );
    }

    if (statusValue) {
        parameters.append(
            "status",
            statusValue
        );


    }


    try {

        const response =
            await fetch(
                "/api/search?" +
                parameters.toString()
            );


        if (!response.ok) {

            throw new Error(
                "Search request failed: " +
                response.status
            );
        }


        const data =
            await response.json();


        if (!data.success) {

            throw new Error(
                "Search failed."
            );
        }


        lastSearchResults =
            data.items || [];


        const language =
            localStorage.getItem(
                "campusFindLanguage"
            ) || "en";


        displaySearchResults(
            lastSearchResults,
            language
        );


    } catch (error) {

        console.error(
            "Search error:",
            error
        );


        const container =
            document.getElementById(
                "results-container"
            );


        if (container) {

            container.innerHTML = `
                <div class="empty-results">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <h3>Unable to complete search</h3>
                    <p>Please try again.</p>
                </div>
            `;
        }
    }
}


// ==================================================
// DISPLAY SEARCH RESULTS
// ==================================================

function displaySearchResults(
    items,
    language = "en"
) {

    const container =
        document.getElementById(
            "results-container"
        );

    const countElement =
        document.getElementById(
            "results-count"
        );


    if (!container) {
        return;
    }


    const t =
        searchTranslations[language] ||
        searchTranslations.en;


    container.innerHTML = "";


    if (!items || items.length === 0) {

        if (countElement) {
            countElement.textContent =
                "0 " + t.itemsFound;
        }


        container.innerHTML = `
            <div class="empty-results">

                <i class="fa-solid fa-box-open"></i>

                <h3>
                    ${t.emptyTitle}
                </h3>

                <p>
                    ${t.emptyDescription}
                </p>

            </div>
        `;

        return;
    }


    if (countElement) {

        countElement.textContent =
            items.length +
            " " +
            t.itemsFound;
    }


    items.forEach(function(item) {

        const card =
            document.createElement("div");

        card.className =
            "search-result-card";


        const imageHTML =
            item.image
                ? `
                    <img
                        src="/uploads/${item.status.toLowerCase()}/${escapeHTML(item.image)}"
                        alt="${escapeHTML(item.item_name)}"
                        class="result-image"
                    >
                  `
                : `
                    <div class="result-image no-image">
                        <i class="fa-solid fa-image"></i>
                    </div>
                  `;


        const statusClass =
            item.status === "Lost"
                ? "lost"
                : "found";


        const statusText =
            item.status === "Lost"
                ? t.lost
                : t.found;


        card.innerHTML = `

            <div class="result-image-container">

                ${imageHTML}

                <span
                    class="status-badge ${statusClass}">
                    ${statusText}
                </span>

            </div>


            <div class="result-content">

                <h3>
                    ${escapeHTML(item.item_name)}
                </h3>


                <p class="result-description">
                    ${escapeHTML(
                        item.description || ""
                    )}
                </p>


                <div class="result-info">

                    <span>
                        <i class="fa-solid fa-layer-group"></i>
                        ${escapeHTML(
                            item.category || ""
                        )}
                    </span>

                    <span>
                        <i class="fa-solid fa-location-dot"></i>
                        ${escapeHTML(
                            item.location || ""
                        )}
                    </span>

                </div>


                <p class="reported-date">

                    <i class="fa-regular fa-clock"></i>

                    ${t.reportedOn}:
                    ${formatReportedDate(
                        item.created_at
                    )}

                </p>


                <button
                    type="button"
                    class="view-details-btn"
                    onclick="viewItemDetails(${item.id})">

                    <i class="fa-solid fa-eye"></i>

                    ${t.viewDetails}

                </button>

            </div>
        `;


        container.appendChild(card);

    });
}


// ==================================================
// VIEW ITEM DETAILS
// ==================================================

function viewItemDetails(itemId) {

    window.location.href =
        "/item/" + itemId;
}


// ==================================================
// FORMAT DATE
// ==================================================

function formatReportedDate(dateValue) {

    if (!dateValue) {
        return "";
    }


    const date =
        new Date(dateValue);


    if (isNaN(date.getTime())) {
        return dateValue;
    }


    return date.toLocaleDateString();
}


// ==================================================
// ESCAPE HTML
// ==================================================

function escapeHTML(value) {

    if (value === null ||
        value === undefined) {

        return "";
    }


    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


// ==================================================
// PAGE LOAD
// ==================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        const savedLanguage =
            localStorage.getItem(
                "campusFindLanguage"
            ) || "en";


        const languageSelect =
            document.getElementById(
                "language"
            );


        if (languageSelect) {

            languageSelect.value =
                savedLanguage;
        }


        applySearchLanguage(
            savedLanguage
        );


        const searchInput =
            document.getElementById(
                "search-input"
            );


        if (searchInput) {

            searchInput.addEventListener(
                "keydown",
                function(event) {

                    if (
                        event.key === "Enter"
                    ) {

                        event.preventDefault();

                        searchItems();
                    }
                }
            );
        }

    }
);