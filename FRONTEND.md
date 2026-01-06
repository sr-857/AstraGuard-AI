# AstraGuard AI - Frontend Documentation

## 🌌 Overview
The AstraGuard AI frontend is a high-performance, immersive single-page application built with **Next.js 16** and **React 19**. It features a modern "Orbital Command" aesthetic, utilizing 3D graphics, smooth animations, and a robust component architecture to deliver a premium user experience.

## 🛠️ Technology Stack
- **Framework**: Next.js (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4 (with OKLCH color spaces)
- **UI Primitives**: Radix UI
- **Animations**: Framer Motion, Tailwind Animate
- **3D Graphics**: Three.js, React Three Fiber (@react-three/fiber)
- **Smooth Scroll**: Lenis
- **Theming**: next-themes

## 🏗️ Architecture

### Directory Structure (`frontend/as_lp`)
```
frontend/as_lp/
├── app/                  # Next.js App Router
│   ├── layout.tsx       # Root layout with ThemeProvider and fonts
│   ├── page.tsx         # Main landing page composition
│   └── globals.css      # Tailwind v4 configuration & global styles
├── components/           # React Components
│   ├── sentient-sphere.tsx  # Interactive 3D Shader Component
│   ├── tech-marquee.tsx     # Infinite scrolling technology list
│   ├── section-blend.tsx    # Visual transition between sections
│   ├── custom-cursor.tsx    # Custom interaction cursor
│   ├── smooth-scroll.tsx    # Lenis scroll wrapper
│   └── [sections].tsx       # Hero, About, Works, etc.
└── lib/                  # Utilities (if applicable)
```

## 🎨 Design System

### Aesthetic: "Orbital Command"
The design follows a futuristic, dark-mode-first approach inspired by spacecraft interfaces.
- **Color Palette**: Uses `oklch()` for perceptually uniform colors. High contrast neon accents against deep space backgrounds.
- **Typography**: "Playfair Display" for headings (classic elegance) mixed with "Geist Mono" for technical data.
- **Visual Effects**:
    - **Noise Overlay**: Subtle grain for texture (`globals.css`).
    - **Glassmorphism**: Translucent panels with background blur.
    - **Micro-interactions**: Hover states, magnetic buttons, and custom cursor fluid dynamics.

## 🔮 Key Components

### 1. Sentient Sphere (`components/sentient-sphere.tsx`)
An interactive 3D icosahedron rendered using React Three Fiber.
- **Shader-based**: Uses custom vertex and fragment shaders (GLSL) for displacement and lighting effects.
- **Interactive**: Responds to mouse movement (rotation and displacement intensity).
- **Performance**: Optimized using `useFrame` for efficient rendering loops.

### 2. Smooth Scroll (`components/smooth-scroll.tsx`)
Implements **Lenis** for momentum-based smooth scrolling, essential for the premium "feel" of the application.

### 3. Tech Marquee (`components/tech-marquee.tsx`)
A continuous infinite loop animation showcasing the technology stack, implemented via CSS keyframes (`animate-marquee-left`, `animate-marquee-right`).

## 🚀 Development

### Prerequisites
- Node.js 18+
- npm or pnpm

### Running Locally
```bash
cd frontend/as_lp
npm install
npm run dev
```
Access at `http://localhost:3000`.

## 📦 Build & Deployment
The application is configured for static export or Node.js server deployment.
```bash
npm run build
npm run start
```
