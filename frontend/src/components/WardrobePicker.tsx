import React, { useEffect, useRef } from 'react';
import {
  OUTFIT_SELECTIONS,
  OUTFIT_KEYS,
  WARDROBE_STRINGS,
  resolveOutfit,
  seasonalOutfit,
  type OutfitSelection,
  type Outfit,
} from '../coucou/mochi/wardrobe';
import { drawWardrobeIcon } from '../coucou/mochi/outfits';
import { Sound } from '../coucou/core/sound';
import { t } from '../coucou/i18n/i18n';

interface WardrobePickerProps {
  currentOutfit: OutfitSelection;
  onSelectOutfit: (outfit: OutfitSelection) => void;
  onPreviewOutfit?: (outfit: Outfit | null) => void;
  onHoverSelection?: (selection: OutfitSelection | null) => void;
}

const ICON_SIZE = 28;

export const WardrobePicker: React.FC<WardrobePickerProps> = ({
  currentOutfit,
  onSelectOutfit,
  onPreviewOutfit,
  onHoverSelection,
}) => {
  const canvasesRef = useRef<Map<OutfitSelection, HTMLCanvasElement>>(new Map());

  // Render 2D icons for each outfit onto canvases
  useEffect(() => {
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const season = seasonalOutfit(new Date());

    OUTFIT_SELECTIONS.forEach((sel) => {
      const canvas = canvasesRef.current.get(sel);
      if (!canvas) return;

      canvas.width = Math.round(ICON_SIZE * dpr);
      canvas.height = Math.round(ICON_SIZE * dpr);
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      drawWardrobeIcon(ctx, ICON_SIZE, sel, season, WARDROBE_STRINGS.autoBadge);
    });
  }, []);

  const handleMouseEnter = (sel: OutfitSelection) => {
    const resolved = resolveOutfit(sel, new Date());
    onPreviewOutfit?.(resolved);
    onHoverSelection?.(sel);
    try {
      Sound.play('hover');
    } catch {}
  };

  const handleMouseLeave = () => {
    onPreviewOutfit?.(null);
    onHoverSelection?.(null);
  };

  const handleClick = (sel: OutfitSelection) => {
    onSelectOutfit(sel);
    try {
      Sound.play('attach');
    } catch {}
  };

  return (
    <div className="flex items-center justify-center p-3 rounded-2xl bg-[#141518] border border-white/8 w-full h-full select-none overflow-hidden">
      {/* Outfits Grid: 2 clean rows showing all 13 skins simultaneously with zero scrolling */}
      <div className="grid grid-cols-7 gap-2.5 items-center justify-items-center w-full max-w-[390px] my-auto">
        {OUTFIT_SELECTIONS.map((sel) => {
          const isSelected = sel === currentOutfit;
          const label = t(OUTFIT_KEYS[sel]);

          return (
            <button
              key={sel}
              type="button"
              title={label}
              aria-label={label}
              onMouseEnter={() => handleMouseEnter(sel)}
              onMouseLeave={handleMouseLeave}
              onClick={() => handleClick(sel)}
              className={`w-[40px] h-[40px] rounded-xl p-0 flex items-center justify-center transition-all cursor-pointer relative ${
                isSelected
                  ? 'bg-white/20 border-2 border-white shadow-md ring-1 ring-white/50 scale-105'
                  : 'bg-white/5 hover:bg-white/12 border border-white/10 hover:border-white/25 hover:scale-105'
              }`}
            >
              <canvas
                ref={(el) => {
                  if (el) canvasesRef.current.set(sel, el);
                  else canvasesRef.current.delete(sel);
                }}
                style={{
                  width: ICON_SIZE,
                  height: ICON_SIZE,
                  pointerEvents: 'none',
                }}
              />
              {isSelected && (
                <span className="absolute -bottom-1 -right-1 w-2.5 h-2.5 rounded-full bg-emerald-400 ring-2 ring-neutral-900" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default WardrobePicker;
