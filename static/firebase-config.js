// Based on your service account, here are some values.
// IMPORTANT: You still need to replace "YOUR_API_KEY_HERE" and "YOUR_APP_ID" 
// with the real values from the Firebase Console (Project Settings > General > Your apps)

const firebaseConfig = {
    apiKey: "AIzaSyD1R6T2vRum5i_Q5ywZhN60NR2F9NVyvoQ",
    authDomain: "rae-manger-ai.firebaseapp.com",
    projectId: "rae-manger-ai",
    storageBucket: "rae-manger-ai.firebasestorage.app",
    messagingSenderId: "431722893941",
    appId: "1:431722893941:web:66bb64059fc8a4c2591e3c",
    measurementId: "G-J6XQTN1T9D"
};

// Initialize Firebase
if (typeof firebase !== 'undefined') {
    firebase.initializeApp(firebaseConfig);
} else {
    console.error("Firebase SDK not loaded yet.");
}
