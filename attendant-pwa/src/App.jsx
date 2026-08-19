import EntryPage from './pages/EntryPage';

/**
 * App — for Week 1.2 this renders only the Entry flow.
 *
 * WHY no router yet: the Exit flow (QR scan -> fetch record -> price ->
 * DB update) is Week 2.1 scope. Adding React Router now, before we know
 * the exact navigation shape between Entry/Exit, would mean guessing at
 * structure we'd likely redo — wiring it up next week, once both pages
 * actually exist, avoids that churn.
 */
export default function App() {
  return <EntryPage />;
}