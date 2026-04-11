import { NavLink } from 'react-router-dom';
import { motion } from 'motion/react';

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/analyze', label: 'Analyze' },
  { to: '/corpus', label: 'Corpus' },
];

export default function Navbar() {
  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-4
                 bg-void-950/80 backdrop-blur-xl border-b border-white/[0.04]"
    >
      <NavLink to="/" className="flex items-center gap-3 group">
        <div className="relative w-8 h-8">
          <div className="absolute inset-0 bg-nova-500 rounded-lg rotate-45 group-hover:rotate-[55deg] transition-transform duration-500" />
          <div className="absolute inset-1 bg-void-950 rounded-md rotate-45 group-hover:rotate-[55deg] transition-transform duration-500" />
          <div className="absolute inset-2 bg-nova-500/80 rounded-sm rotate-45 group-hover:rotate-[55deg] transition-transform duration-500" />
        </div>
        <span className="font-display text-xl font-bold text-white tracking-tight">
          Novelity<span className="text-nova-500">Net</span>
        </span>
      </NavLink>

      <div className="flex items-center gap-1">
        {links.map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `relative px-5 py-2 rounded-lg text-sm font-medium transition-all duration-300 ${
                isActive
                  ? 'text-nova-400 bg-nova-500/[0.08]'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-white/[0.03]'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </div>
    </motion.nav>
  );
}
