import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './Workspace';
import './styles.css';
import './phase3.css';
import './phase4.css';
createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);
