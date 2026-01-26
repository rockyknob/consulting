// --- frontend/server.js ---
import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import fetch from 'node-fetch'; // For calling backend API
import dotenv from 'dotenv';
import session from 'express-session';
import passport from 'passport';
import GoogleStrategy from 'passport-google-oauth20';
import LinkedInStrategy from 'passport-linkedin-oauth2';
import GitHubStrategy from 'passport-github2';
import pg from 'pg';
import connectPgSimple from 'connect-pg-simple';
import LocalStrategy from 'passport-local'; // NEW: Import Local Strategy
import flash from 'connect-flash';

// --- Load Environment Variables ---
dotenv.config({ path: '.env' });
console.log("NODE_ENV:", process.env.NODE_ENV); // Check environment
if (!process.env.SESSION_SECRET) { console.error("FATAL: SESSION_SECRET not set in frontend/.env!"); process.exit(1); }
if (!process.env.DATABASE_URL) { console.error("FATAL: DATABASE_URL not set in frontend/.env (needed for session store)!"); process.exit(1); }


// Configure __dirname for ES Modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = process.env.PORT || 3001;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on port ${PORT}`);
});

// --- Database & Session Store Setup ---
const PgSession = connectPgSimple(session);
const { Pool } = pg;
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  // Add SSL if required by your Postgres provider (like Vercel Postgres)
  ssl: { rejectUnauthorized: false }
});
const sessionStore = new PgSession({
  pool : pool,                // Connection pool
  tableName : 'user_sessions', // Table name for sessions
  createTableIfMissing: true   // Automatically create session table if needed
});

// --- Middleware ---
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));

// Session Middleware (BEFORE Passport)
app.use(session({
  store: sessionStore,
  secret: process.env.SESSION_SECRET, // Loaded from .env
  resave: false,
  saveUninitialized: false,
  cookie: {
      secure: process.env.NODE_ENV === 'production', // Use secure cookies in production
      maxAge: 1000 * 60 * 60 * 24 * 7, // 7 days
      httpOnly: true, // Helps prevent XSS
      sameSite: 'lax' // Mitigate CSRF
    }
}));
app.use(express.urlencoded({ extended: false }));
// Parse JSON bodies (as sent by API clients, good practice to include)
app.use(express.json());

// Passport Middleware
app.use(passport.initialize());
app.use(passport.session()); // Link Passport to the session
app.use(flash());
// --- Backend API URL ---
const backendApiUrl = process.env.BACKEND_API_URL || 'http://127.0.0.1:8000';
const backendUserApiEndpoint = `${backendApiUrl}/api/v1/users/find-or-create`;
const backendUserIdApiEndpoint = `${backendApiUrl}/api/v1/users`;
const backendLoginApiEndpoint = `${backendApiUrl}/api/v1/auth/login`; // NEW
const backendSignupApiEndpoint = `${backendApiUrl}/api/v1/auth/signup`; // NEW
const contentApiEndpoint = `${backendApiUrl}/api/v1/content`;

// --- Passport Strategy Configuration ---

// Verify callback function - calls backend to find/create user
async function verifyCallback(provider, accessToken, refreshToken, profile, done) {
    console.log(`Passport Verify Callback for ${provider}, Profile ID: ${profile.id}`);
    const userData = {
        provider: provider,
        provider_id: profile.id,
        email: profile.emails?.[0]?.value || null, // Primary email if available
        display_name: profile.displayName || profile.username || `${provider} User`,
        profile_picture_url: profile.photos?.[0]?.value || null
    };

    try {
        console.log(`Calling backend: POST ${backendUserApiEndpoint}`);
        const response = await fetch(backendUserApiEndpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });

        if (!response.ok) {
             const errorBody = await response.text();
             console.error(`Backend find-or-create failed: ${response.status}`, errorBody);
             return done(new Error(`Backend error during login (${response.status})`), null);
        }

        const userFromBackend = await response.json(); // Expects UserRead schema
        console.log(`User processed by backend (ID: ${userFromBackend?.id})`);

        if (!userFromBackend || !userFromBackend.id) {
             return done(new Error("Backend did not return valid user data."), null);
        }

        // Pass the user object received from backend (with OUR internal ID) to Passport
        return done(null, userFromBackend);

    } catch (err) {
        console.error(`Error during verify callback for ${provider}:`, err);
        return done(err, null);
    }
}
passport.use(new LocalStrategy.Strategy(
    { usernameField: 'email' }, // Tell Passport to use 'email' field instead of 'username'
    async (email, password, done) => {
        console.log(`Local strategy verify attempt for email: ${email}`);
        try {
             // Call backend login validation endpoint
             const response = await fetch(backendLoginApiEndpoint, {
                 method: 'POST',
                 headers: { 'Content-Type': 'application/json' },
                 body: JSON.stringify({ email: email, password: password }) // Send email/password
             });

             if (!response.ok) {
                 // Backend responded with an error (e.g., 401 Unauthorized)
                 let errorMsg = 'Incorrect email or password.'; // Default
                 try {
                     const result = await response.json();
                     errorMsg = result.detail || errorMsg; // Use backend detail if available
                 } catch { /* Ignore if body isn't JSON */ }
                 console.warn(`Local login failed for ${email}: Status ${response.status}`);
                 return done(null, false, { message: errorMsg }); // Tell Passport login failed, pass message to flash
             }

             const userFromBackend = await response.json(); // Login successful, backend returned user data
             console.log(`Local login successful for ${email}, backend user ID: ${userFromBackend?.id}`);
             if (!userFromBackend || !userFromBackend.id) {
                  return done(new Error("Backend login successful but returned invalid user data."), null);
             }
             // Pass user object from backend to serializeUser
             return done(null, userFromBackend);

        } catch (err) {
             console.error(`Error during local strategy fetch for ${email}:`, err);
             return done(err); // Pass system/network errors to Passport
        }
    }
));

// Google Strategy
if (process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET) {
    passport.use(new GoogleStrategy.Strategy({
        clientID: process.env.GOOGLE_CLIENT_ID,
        clientSecret: process.env.GOOGLE_CLIENT_SECRET,
        callbackURL: process.env.GOOGLE_CALLBACK_URL || "/auth/google/callback"
      },
      (accessToken, refreshToken, profile, done) => verifyCallback('google', accessToken, refreshToken, profile, done)
    ));
} else { console.warn("Google OAuth credentials incomplete."); }



// GitHub Strategy
if (process.env.GITHUB_CLIENT_ID && process.env.GITHUB_CLIENT_SECRET) {
     passport.use(new GitHubStrategy.Strategy({
        clientID: process.env.GITHUB_CLIENT_ID,
        clientSecret: process.env.GITHUB_CLIENT_SECRET,
        callbackURL: process.env.GITHUB_CALLBACK_URL || "/auth/github/callback",
        scope: [ 'user:email' ]
      },
       (accessToken, refreshToken, profile, done) => verifyCallback('github', accessToken, refreshToken, profile, done)
    ));
} else { console.warn("GitHub OAuth credentials incomplete."); }

// Passport Session Serialization/Deserialization
passport.serializeUser((user, done) => {
    // Store only the internal user ID from *our* database in the session
    console.log("Serializing user ID:", user.id);
    done(null, user.id);
});

passport.deserializeUser(async (id, done) => {
    // Retrieve user details from *our* backend using the stored ID
    console.log("Deserializing user ID:", id);
    try {
        // Call backend GET /api/v1/users/{id} endpoint
        // WARNING: This backend endpoint needs proper auth itself in production
        const userApiUrl = `${backendUserIdApiEndpoint}/${id}`;
        console.log(`Workspaceing user details from: ${userApiUrl}`);
        const response = await fetch(userApiUrl);
        if (!response.ok) {
            throw new Error(`Backend could not retrieve user ${id}: Status ${response.status}`);
        }
        const user = await response.json(); // Expects UserRead schema
        if (user) {
            done(null, user); // Attach full user object from backend to req.user
        } else {
            done(new Error(`User with ID ${id} not found in backend`), null);
        }
    } catch (err) {
         console.error(`Error deserializing user ID ${id}:`, err);
         done(err, null);
    }
});

// Middleware to Pass User to All Templates
app.use((req, res, next) => {
  res.locals.currentUser = req.user; // Make user available in EJS as 'currentUser'
  res.locals.isAuthenticated = req.isAuthenticated(); // Pass boolean flag too
  console.log(`Request User (from session):`, req.user ? {id: req.user.id, name: req.user.display_name} : 'Not Authenticated');
  next();
});

// --- Authentication Routes ---
app.get('/auth/google', passport.authenticate('google', { scope: ['profile', 'email'] }));
app.get('/auth/google/callback', passport.authenticate('google', { failureRedirect: '/', successRedirect: '/dashboard' }));



app.get('/auth/github', passport.authenticate('github', { scope: [ 'user:email' ] }));
app.get('/auth/github/callback', passport.authenticate('github', { failureRedirect: '/', successRedirect: '/dashboard' }));
app.get('/login', (req, res) => {
    // Pass flash messages to the template
    res.render('login', { pageTitle: "Sign In", message: req.flash('error') });
});

app.post('/login', passport.authenticate('local', {
    successRedirect: '/dashboard', // Where to go on success
    failureRedirect: '/login',     // Where to go on failure
    failureFlash: true             // Use flash messages for errors
}));

// --- NEW Local Signup Routes ---
 app.get('/signup', (req, res) => {
    res.render('signup', { pageTitle: "Sign Up", message: req.flash('error'), formData: {} }); // Pass empty formData initially
});

 app.post('/signup', async (req, res, next) => {
     console.log("Received POST /signup");
     const { display_name, email, password, confirm_password } = req.body;

     // Basic validation
     if (!display_name || !email || !password || !confirm_password) {
          req.flash('error', 'Please fill out all fields.');
          return res.render('signup', { pageTitle: "Sign Up", message: req.flash('error'), formData: req.body });
     }
     if (password !== confirm_password) {
          req.flash('error', 'Passwords do not match.');
          return res.render('signup', { pageTitle: "Sign Up", message: req.flash('error'), formData: req.body });
     }
     if (password.length < 8) {
          req.flash('error', 'Password must be at least 8 characters.');
          return res.render('signup', { pageTitle: "Sign Up", message: req.flash('error'), formData: req.body });
     }

     try {
          // Call backend signup endpoint
          const response = await fetch(backendSignupApiEndpoint, {
               method: 'POST',
               headers: { 'Content-Type': 'application/json' },
               body: JSON.stringify({ email, password, display_name })
          });

          if (!response.ok) {
               let errorMsg = 'Signup failed. Please try again.';
               try {
                   const result = await response.json();
                   errorMsg = result.detail || errorMsg; // Use backend error message if available
               } catch { /* Ignore if response not JSON */ }
               req.flash('error', errorMsg);
               return res.render('signup', { pageTitle: "Sign Up", message: req.flash('error'), formData: req.body });
          }

          // Signup successful on backend
          console.log("Signup successful on backend for:", email);
          req.flash('success', 'Account created successfully! Please log in.'); // Add success message
          return res.redirect('/login'); // Redirect to login page

          // --- OR Automatically log in user (more complex) ---
          // const newUser = await response.json();
          // req.login(newUser, function(err) { // req.login provided by Passport
          //      if (err) { return next(err); }
          //      return res.redirect('/dashboard');
          // });
          // --- End Auto Login ---

     } catch (error) {
          console.error("Error calling backend signup:", error);
          req.flash('error', 'An error occurred during signup. Please try again.');
          return res.render('signup', { pageTitle: "Sign Up", message: req.flash('error'), formData: req.body });
     }
 });
// Logout Route
app.get('/logout', (req, res, next) => {
  req.logout(err => { // req.logout is async and requires callback
    if (err) { return next(err); }
    req.session.destroy(err => { // Destroy session data in store
        if (err) { console.error("Error destroying session:", err); return next(err); }
        res.clearCookie('connect.sid'); // Clear session cookie (default name)
        console.log("User logged out, session destroyed.");
        res.redirect('/');
    });
  });
});

// Middleware to Protect Routes
function ensureAuthenticated(req, res, next) {
  if (req.isAuthenticated()) { return next(); }
  console.log("Auth check failed, redirecting to home.");
  res.redirect('/');
}

// Helper to fetch base content
async function getBaseContent() {
    console.log(`[getBaseContent] Attempting fetch from ${contentApiEndpoint}`);
    let response;
    try {
        response = await fetch(contentApiEndpoint, { timeout: 5000 });
        console.log(`[getBaseContent] Received response status: ${response.status}`);
        if (!response.ok) {
            const errorBody = await response.text();
            console.error(`[getBaseContent] API Error Status: ${response.status}. Body: ${errorBody}`);
            throw new Error(`API request failed with status ${response.status}`);
        }
        const jsonData = await response.json();
        console.log("[getBaseContent] Successfully parsed JSON.");
        // Quick check if essential data is present
        if (!jsonData || !jsonData.hero) {
            console.warn("[getBaseContent] Parsed JSON seems incomplete.");
            throw new Error("Incomplete content received from backend.");
        }
        return jsonData;
    } catch (error) {
        console.error("[getBaseContent] Entered CATCH block:", error.message);
        // Return default structure on ANY error
        return {
            hero: null, services: [], products: [], clients: [], testimonials: [],
            custom_consulting_packages: [], // Include empty array here
            current_year: new Date().getFullYear()
        };
    }
}

app.get('/', async (req, res) => {
    console.log(`GET / request received.`);
    const contentData = await getBaseContent();
    const fetchError = (!contentData || !contentData.hero) ? "Failed to load main content from backend." : null;
    res.render('index', { content: contentData, error: fetchError });
});

app.get('/financial-analyzer', async (req, res) => {
     console.log(`GET /financial-analyzer request received.`);
     const baseContent = await getBaseContent(); // Fetch for navbar/footer data
     res.render('financial-analyzer', { pageTitle: "AI Financial Analyzer", current_year: baseContent.current_year, content: baseContent });
});

app.get('/startup-consultation', async (req, res) => {
     console.log(`GET /startup-consultation request received.`);
     const baseContent = await getBaseContent();
     res.render('startup-consultation', { pageTitle: "AI Startup Consultation", current_year: baseContent.current_year, content: baseContent });
});

app.get('/custom-consulting', async (req, res) => {
    console.log(`GET /custom-consulting request received.`);
    const contentData = await getBaseContent();
    const fetchError = (!contentData || !contentData.custom_consulting_packages) ? "Failed to load consulting packages." : null;
    res.render('custom-consulting', { pageTitle: "Custom Consulting Solutions", content: contentData, error: fetchError });
});

// NEW Route for Tracking Page - only renders the static EJS page
app.get('/track-request', (req, res) => {
    console.log(`GET /track-request request received.`);
    res.render('track_request', { pageTitle: "Track Your Request" });
});

// --- Start Server ---
//app.listen(port, () => {
  //  console.log(`Frontend server running at http://localhost:${port}`);
//});

// --- NEW Protected Routes ---
app.get('/dashboard', ensureAuthenticated, async (req, res) => {
    console.log("Accessing protected dashboard for user:", res.locals.currentUser?.id);
    res.render('dashboard', { pageTitle: "Dashboard" }); // currentUser passed via res.locals
});

app.get('/profile', ensureAuthenticated, async (req, res) => {
     console.log("Accessing protected profile for user:", res.locals.currentUser?.id);
     res.render('profile', { pageTitle: "Your Profile" }); // currentUser passed via res.locals
});



