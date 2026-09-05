import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";

import { isAuthenticated } from "./auth.js";

function ProtectedHome() {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  return <Home />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>

        <Route
          path="/login"
          element={<Login />}
        />

        <Route
          path="/register"
          element={<Register />}
        />

        <Route
          path="/"
          element={<ProtectedHome />}
        />

        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />

      </Routes>
    </BrowserRouter>
  );
}

export default App;