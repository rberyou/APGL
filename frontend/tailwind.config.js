/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1f2937",
        paper: "#f7f7f3",
        line: "#d9ddd4",
        teal: "#0f766e",
        ember: "#b45309"
      }
    }
  },
  plugins: []
};

