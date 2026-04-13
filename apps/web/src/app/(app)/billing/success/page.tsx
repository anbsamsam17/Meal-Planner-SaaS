"use client";
// apps/web/src/app/(app)/billing/success/page.tsx
// Page retour apres paiement Stripe reussi
// Phase 2 -- confetti via @/components/motion, recap features debloquees, CTA

import { useEffect, useState } from "react";
import Link from "next/link";
import { MotionDiv, MotionLi, MotionUl, AnimatePresence } from "@/components/motion";
import { CheckCircle, BookOpen, Refrigerator, Star, Sparkles } from "lucide-react";

const UNLOCKED_FEATURES = [
  {
    icon: BookOpen,
    label: "Livres PDF hebdomadaires",
    desc: "Telechargez votre semaine en PDF pour cuisiner sans internet.",
  },
  {
    icon: Refrigerator,
    label: "Mode frigo",
    desc: "Dites ce que vous avez dans le frigo, on suggere les recettes.",
  },
  {
    icon: Star,
    label: "Recettes premium",
    desc: "Acces a +500 recettes exclusives de chefs.",
  },
  {
    icon: Sparkles,
    label: "Plans illimites",
    desc: "Generez autant de semaines que vous voulez.",
  },
];

// Confetti simple -- 30 particules colorees via MotionDiv
function Confetti() {
  const particles = Array.from({ length: 30 }, (_, i) => i);
  const colors = ["#C8674A", "#6B7F45", "#F5EFE7", "#E8C5B0", "#4A6741"];

  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden>
      {particles.map((i) => {
        const color = colors[i % colors.length] as string;
        const left = `${Math.random() * 100}%`;
        const duration = 1.5 + Math.random() * 2;
        const delay = Math.random() * 0.8;
        const size = 6 + Math.random() * 10;

        return (
          <MotionDiv
            key={i}
            style={{
              position: "absolute",
              left,
              top: "-10px",
              width: size,
              height: size,
              borderRadius: Math.random() > 0.5 ? "50%" : "2px",
              backgroundColor: color,
            }}
            initial={{ y: -20, opacity: 1, rotate: 0 }}
            animate={{
              y: "110vh",
              opacity: [1, 1, 0],
              rotate: Math.random() > 0.5 ? 360 : -360,
            }}
            transition={{ duration, delay, ease: "easeIn" }}
          />
        );
      })}
    </div>
  );
}

export default function BillingSuccessPage() {
  const [showConfetti, setShowConfetti] = useState(false);

  useEffect(() => {
    setShowConfetti(true);
    const timer = setTimeout(() => setShowConfetti(false), 4000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="relative min-h-screen bg-[#fff8f6] px-4 py-12">
      <AnimatePresence>{showConfetti && <Confetti />}</AnimatePresence>

      <div className="mx-auto max-w-lg">
        {/* Icone succes animee */}
        <MotionDiv
          className="mb-6 flex justify-center"
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 260, damping: 20 }}
        >
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-green-100">
            <CheckCircle className="h-10 w-10 text-green-600" aria-hidden />
          </div>
        </MotionDiv>

        {/* Titre */}
        <MotionDiv
          className="mb-2 text-center text-2xl font-bold text-neutral-900"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <h1>Bienvenue dans le plan Famille !</h1>
        </MotionDiv>
        <MotionDiv
          className="mb-8 text-center text-sm text-neutral-500"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.35 }}
        >
          <p>Votre abonnement est actif. Voici ce que vous venez de debloquer.</p>
        </MotionDiv>

        {/* Features debloquees */}
        <MotionUl
          className="mb-8 space-y-3"
          initial="hidden"
          animate="visible"
          variants={{
            visible: { transition: { staggerChildren: 0.1, delayChildren: 0.4 } },
            hidden: {},
          }}
        >
          {UNLOCKED_FEATURES.map(({ icon: Icon, label, desc }) => (
            <MotionLi
              key={label}
              className="flex items-start gap-3 rounded-xl border border-neutral-100 bg-white px-4 py-3 shadow-sm"
              variants={{
                hidden: { opacity: 0, x: -16 },
                visible: { opacity: 1, x: 0 },
              }}
            >
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-primary-100">
                <Icon className="h-5 w-5 text-primary-600" aria-hidden />
              </div>
              <div>
                <p className="text-sm font-semibold text-neutral-900">{label}</p>
                <p className="text-xs text-neutral-500">{desc}</p>
              </div>
            </MotionLi>
          ))}
        </MotionUl>

        {/* CTA */}
        <MotionDiv
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9 }}
        >
          <Link
            href="/dashboard"
            className="inline-flex min-h-[44px] w-full items-center justify-center rounded-lg bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-primary-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2"
          >
            Generer ma premiere semaine premium
          </Link>
        </MotionDiv>
      </div>
    </div>
  );
}
