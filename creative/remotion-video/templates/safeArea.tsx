// Instagram/sosyal medya GÜVENLİ ALAN (safe zone) yardımcıları.
// design.ts'e safeInsets'i, kompozisyona SafeArea wrapper'ını kopyala.
//
// Reels/Story 9:16 (1080x1920): Instagram UI öğeleri görselin ÜZERİNE biner —
// üst ~220px kullanıcı adı, alt ~320px açıklama+butonlar, sağ ~120px aksiyon
// kolonu, sol ~60px. Merkezi güvenli alan ~1010x1440px.
// (Kaynak: Verve/Meta/Minta/FizzyPop safe-zone kılavuzları, 2025.)
// 1:1 feed'de UI görselin DIŞINDA olduğundan modest margin yeter.

export function safeInsets(width: number, height: number) {
  const portrait = height >= width;
  const reels = portrait && height / width > 1.4; // 9:16 dikey
  if (reels) {
    return {
      top: Math.round(height * 0.12),    // ~230px (kullanıcı adı)
      bottom: Math.round(height * 0.18), // ~345px (açıklama+butonlar)
      left: Math.round(width * 0.06),    // ~65px
      right: Math.round(width * 0.11),   // ~120px (aksiyon kolonu)
      reels: true,
    };
  }
  // 1:1 feed (ve 4:5): hafif kenar boşluğu yeterli
  return {
    top: Math.round(height * 0.06),
    bottom: Math.round(height * 0.07),
    left: Math.round(width * 0.05),
    right: Math.round(width * 0.05),
    reels: false,
  };
}

// ---- Kompozisyonda (MaarifVideo.tsx) ----
// import { AbsoluteFill } from 'remotion';
// import { safeInsets } from './design';
//
// Kritik öğeler bu çerçevenin içinde kalır; dekoratif Background TAM EKRAN kalır.
//
// const SafeArea: React.FC<{ width:number; height:number; children:React.ReactNode; center?:boolean }>
//   = ({ width, height, children, center }) => {
//   const s = safeInsets(width, height);
//   return (
//     <AbsoluteFill style={{
//       top: s.top, bottom: s.bottom, left: s.left, right: s.right,
//       ...(center ? { justifyContent:'center', alignItems:'center' } : {}),
//     }}>
//       {children}
//     </AbsoluteFill>
//   );
// };
//
// Kullanım: Background tam ekran, üstüne <SafeArea> ile kritik içerik.
// Küreyi güvenli banda ortalamak için: transform: `translateY(${(s.top-s.bottom)/2}px)`.

// ---- Doğrulama: drawbox ile güvensiz bantları işaretle ----
// ffmpeg -y -i out_9x16.mp4 -vf "select=eq(n\,420)" -frames:v 1 frame.png
// ffmpeg -y -i frame.png -vf \
//   "drawbox=x=0:y=0:w=1080:h=220:color=red@0.4:t=fill,\
//    drawbox=x=0:y=1600:w=1080:h=320:color=red@0.4:t=fill,\
//    drawbox=x=960:y=220:w=120:h=1380:color=orange@0.3:t=fill" frame_marked.png
// → vision_analyze: "bu kırmızı/turuncu bantlara giren kritik öğe var mı?"
