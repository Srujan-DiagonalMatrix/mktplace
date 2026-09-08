import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import VehicleNeeds from './vehicle-needs/VehicleNeeds';
import './vehicle-needs/vehicle-needs.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/vehicle-needs" element={<VehicleNeeds />} />
        <Route path="*" element={<Navigate to="/vehicle-needs" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode><App /></React.StrictMode>,
);
