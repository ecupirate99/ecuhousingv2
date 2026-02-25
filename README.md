# ECU Residence Hall Handbook Chatbot 🏴‍☠️

A RAG-powered (Retrieval-Augmented Generation) chatbot designed to answer questions about East Carolina University (ECU) Residence Hall policies using the official handbook.

## 🚀 Features
- **PDF Indexing**: Upload any handbook PDF to index into a Supabase Vector Store.
- **Smart Chat**: Powered by Groq (Llama 3.3 70B) and Google Gemini Embeddings.
- **ECU Branded UI**: A clean, light-mode interface matching ECU Housing aesthetics.
- **Citations**: Always provides source page numbers for its answers.

## 🛠 Tech Stack
- **Backend**: FastAPI (Python)
- **Frontend**: Tailwind CSS, Vanilla JS
- **Vector DB**: Supabase (pgvector)
- **AI Models**: 
  - Llama 3.3 70B (via Groq)
  - Gemini Embedding v1 (via Google)

## 📦 Setup & Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd llamaindex
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file with:
   ```env
   SUPABASE_URL=your_url
   SUPABASE_ANON_KEY=your_key
   SUPABASE_DB_URL=postgresql://your_db_connection_string
   GOOGLE_API_KEY=your_google_key
   GROQ_API_KEY=your_groq_key
   ```

4. **Run Locally**:
   ```bash
   python main.py
   ```

## ☁️ Deployment

### GitHub
Push this code to a private or public repository. Ensure `.env` is NOT uploaded (already handled by `.gitignore`).

### Vercel
1. Connect your GitHub repository to Vercel.
2. Add your `.env` variables to Vercel's Environment Variables settings.
3. Deploy! (Settings are pre-configured in `vercel.json`).
