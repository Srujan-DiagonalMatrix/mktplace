import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const steps = ['Vehicle Selection', 'Business Needs', 'Vehicle Details', 'Driver Details', 'Risk Details', 'Summary'];
const selectOptions = {
  vehicles: ['1', '2', '3', '4', '5+'],
  doors: ['Any', '2', '3', '4', '5'],
  manufacturer: ['Any', 'Audi', 'BMW', 'Ford', 'Mercedes-Benz', 'Tesla', 'Toyota', 'Volkswagen'],
  fuel: ['Any', 'Petrol', 'Diesel', 'Electric', 'Hybrid'],
  colour: ['Any', 'Black', 'Blue', 'Grey', 'Red', 'Silver', 'White'],
  year: ['Any', '2026', '2025', '2024', '2023', '2022', '2021 or earlier'],
};

function Header() {
  return <>
    <header className="topbar">
      <a className="brand" href="/" aria-label="ROVE home"><span>R</span> ROVE</a>
      <nav aria-label="Primary navigation">
        <a href="#vehicles">Vehicles <small>⌄</small></a>
        <a href="#industries">Industries <small>⌄</small></a>
        <a href="#about">About Us</a>
      </nav>
      <div className="account-links"><a href="#account">◉ Account</a><a href="#saved">♡ Saved</a></div>
    </header>
    <nav className="progress" aria-label="Application progress">
      {steps.map((step, index) => <div className={index === 0 ? 'active' : ''} key={step}>
        <span>{index === 0 ? '✓' : index + 1}</span>{step}
      </div>)}
    </nav>
  </>;
}

function SelectField({ label, value, onChange, options }) {
  return <label className="field"><span>{label}</span><select value={value} onChange={onChange}>
    {options.map(option => <option key={option}>{option}</option>)}
  </select></label>;
}

function Choice({ label, selected, onClick, icon }) {
  return <button type="button" role="radio" aria-checked={selected} className={`choice ${selected ? 'selected' : ''}`} onClick={onClick}>
    {icon && <span className={`vehicle-icon ${icon}`} aria-hidden="true">▰</span>}<strong>{label}</strong><i />
  </button>;
}

export default function VehicleNeeds() {
  const navigate = useNavigate();
  const [vehicleType, setVehicleType] = useState('Van');
  const [carType, setCarType] = useState('Compact');
  const [form, setForm] = useState({ vehicles: '1', doors: 'Any', manufacturer: 'Any', fuel: 'Any', colour: 'Any', year: 'Any', requirements: '' });
  const update = key => event => setForm(current => ({ ...current, [key]: event.target.value }));
  const save = () => localStorage.setItem('roveVehicleNeeds', JSON.stringify({ vehicleType, carType, ...form }));

  return <div className="app-shell">
    <Header />
    <main>
      <section className="intro"><h1>Vehicle Needs</h1><p>Add additional services to your contract here.</p></section>
      <section className="section vehicle-section">
        <h2>Vehicle Type</h2><p>Tell us what type of vehicle you're looking for.</p>
        <div className="vehicle-grid">
          <div><span className="label">Vehicle Type</span><div className="choice-row" role="radiogroup" aria-label="Vehicle Type">
            {['Van', 'Car'].map(item => <Choice key={item} label={item} selected={vehicleType === item} onClick={() => setVehicleType(item)} />)}
          </div></div>
          <SelectField label="Number of Vehicles" value={form.vehicles} onChange={update('vehicles')} options={selectOptions.vehicles} />
          <div><span className="label">Car Type</span><div className="car-grid" role="radiogroup" aria-label="Car Type">
            {[['Compact','compact'], ['Saloon','saloon'], ['SUV','suv'], ['Not Sure','unknown']].map(([item, icon]) => <Choice key={item} label={item} icon={icon} selected={carType === item} onClick={() => setCarType(item)} />)}
          </div></div>
        </div>
      </section>
      <section className="section details-section">
        <h2>Vehicle Details</h2><p>These are optional questions that we can use to refine your search even further.</p>
        <div className="details-panel">
          <SelectField label="Number of Doors" value={form.doors} onChange={update('doors')} options={selectOptions.doors} />
          <SelectField label="Manufacturer" value={form.manufacturer} onChange={update('manufacturer')} options={selectOptions.manufacturer} />
          <SelectField label="Fuel Type" value={form.fuel} onChange={update('fuel')} options={selectOptions.fuel} />
          <SelectField label="Colour" value={form.colour} onChange={update('colour')} options={selectOptions.colour} />
          <SelectField label="Year" value={form.year} onChange={update('year')} options={selectOptions.year} />
          <label className="requirements"><span>Are there any features you would like to add? <em>Personalisation</em></span>
            <textarea placeholder="This will help us personalise our recommendations to you." value={form.requirements} onChange={update('requirements')} />
          </label>
        </div>
      </section>
    </main>
    <footer className="actions">
      <button className="save" onClick={save}>▱&nbsp; Save for later</button>
      <div><button className="skip" onClick={() => navigate('/business-needs')}>Skip</button><button className="next" onClick={() => { save(); navigate('/business-needs'); }}>Add business needs <b>→</b></button></div>
    </footer>
  </div>;
}
