import { useEffect, useState } from 'react';
import { supabase, setUserIdLocal, getUserIdLocal, ensureAnonymousUserId } from '../../../lib/supabase';
import { startTelegramLink, getTelegramLinkStatus } from '../../../api/client';

export default function AuthBar() {
  const [userId, setUserId] = useState<string | null>(getUserIdLocal());
  const [linkToken, setLinkToken] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      if (!supabase) {
        const id = ensureAnonymousUserId();
        if (!mounted) return;
        setUserId(id);
        return;
      } else {
        const { data } = await supabase.auth.getSession();
        const uid = data.session?.user?.id || null;
        if (!mounted) return;
        if (uid) {
          setUserId(uid);
          setUserIdLocal(uid);
        }
        // subscribe to future auth changes
        supabase.auth.onAuthStateChange((_event: any, session: any) => {
          const u = session?.user?.id || null;
          setUserId(u);
          setUserIdLocal(u);
        });
      }
    })();
    return () => { mounted = false; };
  }, []);

  const signIn = async () => {
    if (!supabase) {
      alert('Anonymous mode is active. No login required.');
      return;
    }
    await supabase.auth.signInWithOAuth({ provider: 'github' });
  };

  const signOut = async () => {
    if (supabase) await supabase.auth.signOut();
    // Revert to anonymous after sign out
    const id = ensureAnonymousUserId();
    setUserId(id);
  };

  const handleConnectTelegram = async () => {
    try {
      // Ensure we have a user before starting Telegram flow
      if (!userId) {
        if (supabase) {
          await supabase.auth.signInWithOAuth({ provider: 'github' });
          return; // OAuth will redirect; continue after sign-in
        } else {
          const id = ensureAnonymousUserId();
          setUserId(id);
        }
      }
      const botUsername = import.meta.env.VITE_TG_BOT_USERNAME as string | undefined;
      if (botUsername) {
        // If already linked, open plain bot URL (no /start); else generate token and open deep link
        const status = await getTelegramLinkStatus().catch(() => ({ linked: false }));
        if (status.linked) {
          window.open(`https://t.me/${botUsername}`, '_blank', 'noopener,noreferrer');
          return;
        }
        const res = await startTelegramLink();
        setLinkToken(res.token);
        window.open(`https://t.me/${botUsername}?start=${encodeURIComponent(res.token)}`, '_blank', 'noopener,noreferrer');
        return;
      }
      // Fallback: no bot username configured → show copyable code
      const res = await startTelegramLink();
      setLinkToken(res.token);
    } catch (e) {
      alert('Failed to start Telegram link. Please try again after signing in.');
    }
  };

  const botUsername = import.meta.env.VITE_TG_BOT_USERNAME as string | undefined;
  const handleCopyCode = async () => {
    if (!linkToken) return;
    try {
      await navigator.clipboard.writeText(`/start ${linkToken}`);
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex items-center gap-3">
      {userId ? (
        <>
          <span className="text-xs text-gray-600 font-light">{supabase ? 'Signed in' : 'Anonymous mode'}</span>
          {supabase && (
            <button onClick={signOut} className="text-xs text-gray-600 hover:text-gray-800 font-light cursor-pointer">Sign out</button>
          )}
          <button onClick={handleConnectTelegram} className="px-3 py-1.5 text-white rounded-full text-xs font-normal cursor-pointer inline-flex items-center gap-1 bg-gradient-to-br from-sky-400 to-rose-200 hover:from-sky-500 hover:to-rose-300 shadow-sm">
            <i className="ri-telegram-fill"></i>
            Connect Telegram
          </button>
          {linkToken && !botUsername && (
            <div className="ml-2 text-xs text-gray-600 font-light flex items-center gap-2">
              <span>Copy this into Telegram:</span>
              <code className="px-1 py-0.5 bg-gray-100 rounded">/start {linkToken}</code>
              <button onClick={handleCopyCode} className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full">Copy</button>
            </div>
          )}
        </>
      ) : (
        <button onClick={signIn} className="px-3 py-1.5 bg-gray-800 text-white rounded-full text-xs font-normal cursor-pointer">
          Sign in
        </button>
      )}
    </div>
  );
}


