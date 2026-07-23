import { useEffect, useRef } from 'react';
import { Transak } from '@transak/ui-js-sdk';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';

interface TransakRampProps {
  isOnRamp?: boolean;
  defaultAmount?: number;
}

export default function TransakRamp({ 
  isOnRamp = true, 
  defaultAmount = 100 
}: TransakRampProps) {
  const transakRef = useRef<any>(null);
  const { user } = useAuth();

  useEffect(() => {
    if (!user?.walletAddress) {
      console.warn("Wallet address non disponibile");
      return;
    }

    const config = {
      apiKey: import.meta.env.VITE_TRANSAK_API_KEY,
      environment: 'PRODUCTION',
      widgetUrl: 'https://global.transak.com',
      
      defaultCryptoCurrency: isOnRamp ? 'BNB' : undefined,
      defaultFiatAmount: defaultAmount.toString(),
      fiatCurrency: 'EUR',
      walletAddress: user.walletAddress,
      
      redirectURL: window.location.href,
      themeColor: '#0ea5e9',
      hideMenu: false,
      isFeeCalculationHidden: false,
    };

    transakRef.current = new Transak(config);
    transakRef.current.init();

    // Event Listeners con chiamata al backend
    Transak.on(Transak.EVENTS.TRANSAK_ORDER_CREATED, (order) => {
      console.log("Ordine creato:", order);
    });

    Transak.on(Transak.EVENTS.TRANSAK_ORDER_SUCCESSFUL, async (order) => {
      console.log("✅ Ordine completato con successo:", order);

      // Invia automaticamente al backend
      try {
        await axios.post(`${import.meta.env.VITE_BACKEND_URL}/api/ramp/transak-webhook`, {
          event: "TRANSAK_ORDER_SUCCESSFUL",
          data: order
        });
        console.log("Transazione salvata correttamente nel DB");
      } catch (err) {
        console.error("Errore nel salvataggio backend:", err);
      }
    });

    Transak.on(Transak.EVENTS.TRANSAK_WIDGET_CLOSE, () => {
      console.log("Widget Transak chiuso");
    });

    return () => {
      if (transakRef.current) {
        transakRef.current.close();
      }
    };
  }, [isOnRamp, defaultAmount, user?.walletAddress]);

  return (
    <div className="w-full max-w-5xl mx-auto">
      <div 
        className="w-full h-[680px] border border-gray-800 rounded-3xl overflow-hidden shadow-2xl bg-black"
        id="transak-container"
      />
    </div>
  );
}
