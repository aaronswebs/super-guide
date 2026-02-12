# super-guide

A simple, modern web-based AI chatbot interface with turn-by-turn conversation functionality.

## Features

- 🤖 Interactive AI chatbot interface
- 💬 Turn-by-turn message display
- ✨ Smooth animations and transitions
- 📱 Responsive design
- 🎨 Modern, gradient-based UI
- ⌨️ Keyboard support (Enter to send)
- 💭 Typing indicators
- 🔄 Real-time message updates

## Getting Started

Simply open `index.html` in your web browser to start chatting with the AI assistant!

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/aaronswebs/super-guide.git
   cd super-guide
   ```

2. Open `index.html` in your browser:
   - Double-click the file, or
   - Use a local server (recommended):
     ```bash
     python -m http.server 8000
     # Then visit http://localhost:8000
     ```

## How It Works

The chatbot interface consists of three main files:

- **index.html** - The main HTML structure
- **styles.css** - Modern, responsive styling
- **script.js** - Interactive chat functionality

### Current Implementation

The current version includes:
- Simulated AI responses based on keyword detection
- Typing indicators for a realistic chat experience
- Smooth scrolling and animations
- Clean, modern UI design

### Future Enhancements

To connect to a real AI backend, modify the `getAIResponse()` function in `script.js` to call your AI API endpoint.

## Technologies Used

- HTML5
- CSS3 (with animations and gradients)
- Vanilla JavaScript (ES6+)

## License

See LICENSE file for details.