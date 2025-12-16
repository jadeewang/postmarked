# postmarked 📮

*your personal postcard artist*

Turn your travel memories into a custom AI-generated postcard. Upload 1-3 photos from a specific trip, and Postmarked will analyze them to create a unique, illustrated postcard with a personalized caption that captures the one-of-a-kind nature of your experience.

▶️ **[Watch Demo Video](https://vimeo.com/1146886743)**

---

## ✨ Features

- **AI Image Analysis**: GPT-4 Vision analyzes your photos to understand colors, scenes, mood, and key elements
- **Smart Aggregation**: Combines insights from multiple photos into a cohesive trip summary
- **Custom Postcard Generation**: DALL-E 3 creates a unique illustration based on your trip
- **Personalized Captions**: AI-written captions that match your chosen tone (artistic, satirical, dramatic, or minimalist)
- **Multiple Art Styles**: Choose from vintage postcard, watercolor, collage, or graphic line art

---

## 🚀 Quick Start (Run Locally)

### Prerequisites

- Python 3.10 or higher
- An OpenAI API key with credits ([get one here](https://platform.openai.com/api-keys))

### Step 1: Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/postmarked.git
cd postmarked
```

### Step 2: Set up the backend

```bash
cd backend

# Create a virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Mac/Linux
# OR
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Add your OpenAI API key

Create a `.env` file in the `backend` folder:

```bash
echo "OPENAI_API_KEY=sk-your-api-key-here" > .env
```

Replace `sk-your-api-key-here` with your actual OpenAI API key.

### Step 4: Run the app

```bash
python app.py
```

### Step 5: Open in your browser

Go to: **http://localhost:5001**

---

## 📖 How to Use

1. **Upload 1-3 photos** from a single trip
2. **Enter your location** (e.g., "Rome, Fall 2024")
3. **Choose an art style**: vintage, watercolor, collage, or line art
4. **Choose a caption tone**: artistic, satirical, dramatic, or minimalist
5. **Click "create postcard"** and wait ~60-90 seconds
6. **Download** your personalized postcard!

---

## 🔑 Getting an OpenAI API Key

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Go to **API Keys** in the left sidebar
4. Click **"Create new secret key"**
5. Copy the key (starts with `sk-`)
6. Add billing/credits to your account (required for API usage)

**Note**: Generating one postcard costs approximately $0.05-0.15 in API credits.

---

## 📁 Project Structure

```
postmarked/
├── backend/
│   ├── app.py              # Main Flask application
│   ├── requirements.txt    # Python dependencies
│   ├── .env               # Your API key (create this)
│   ├── static/            # Frontend files served by Flask
│   │   ├── index.html
│   │   ├── styles.css
│   │   └── script.js
│   └── services/
│       ├── image_analysis.py   # GPT-4 Vision analysis
│       ├── aggregation.py      # Album-level aggregation
│       └── generation.py       # DALL-E & caption generation
└── frontend/              # Original frontend source files
    ├── index.html
    ├── styles.css
    └── script.js
```

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **AI**: OpenAI GPT-4 Vision, GPT-4, DALL-E 3
- **Frontend**: HTML, CSS, JavaScript

---

## ⚠️ Troubleshooting

### "OPENAI_API_KEY environment variable is not set"
Make sure you created the `.env` file in the `backend` folder with your API key.

### "You exceeded your current quota"
Add credits to your OpenAI account at [platform.openai.com/settings/organization/billing](https://platform.openai.com/settings/organization/billing)

### Postcard generation takes too long
This is normal! The process takes 60-90 seconds:
- ~30 seconds for image analysis
- ~30 seconds for DALL-E image generation
- ~5 seconds for caption generation

### Port 5001 is already in use
Another app is using the port. Either stop that app, or change the port in `app.py` (last line).

---

## 📝 License

MIT License - feel free to use, modify, and share!

---

## 🙏 Acknowledgments

Built by Jade Wang for CNMPS 3002 with the help of Claude, Orchids, and Cursor ✨.

