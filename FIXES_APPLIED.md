# Fixes Applied to Fishing Mini-App

## Date: 2026-09-06

## Issues Fixed

### 1. ✅ Stars Top-Up Redirect Issue
**Problem**: Stars payment redirected to wrong bot (`your_bot` placeholder)
**Solution**: 
- Modified `fishingScreen.ts` to use `tgService.webApp.openInvoice()` directly
- Added `openInvoice` method to `TelegramWebApp` interface in `telegram.ts`
- Exposed `webApp` property in `TelegramService` class
- Now uses Telegram's native invoice dialog within the app

**Files Modified**:
- `webapp/ui_from_testpers/src/ui/fishingScreen.ts` (line ~760)
- `webapp/ui_from_testpers/src/modules/telegram.ts`

### 2. ✅ TON Manifest Error
**Problem**: TON Connect showing "manifest error" when trying to connect wallet
**Solution**:
- Added route `/tonconnect-manifest.json` in `webapp/app.py`
- Serves manifest from `webapp/ui_from_testpers/public/tonconnect-manifest.json`
- Manifest is now accessible at `https://your-domain.com/tonconnect-manifest.json`

**Files Modified**:
- `webapp/app.py` (added route before `/health`)

### 3. ✅ Fish Result Modal Not Showing
**Problem**: No modal/alert shown after catching fish
**Solution**:
- Fixed timing issue in `showFishModal()` - changed from `requestAnimationFrame` to `setTimeout(10ms)`
- This ensures the modal element is fully inserted into DOM before adding `.visible` class
- CSS transitions now work correctly

**Files Modified**:
- `webapp/ui_from_testpers/src/ui/fishingScreen.ts` (`showFishModal` method)

### 4. ✅ Improved Slot Animation
**Problem**: Slot just scaled images, no smooth vertical scroll effect
**Solution**:
- Rewrote `spinSlots()` to use CSS transforms (`translateY` + `scale`)
- Added smooth opacity transition during scroll
- Increased spin count to 50 for longer animation
- Progressive slowdown effect (increases interval time)

**Files Modified**:
- `webapp/ui_from_testpers/src/ui/fishingScreen.ts` (`spinSlots` method)
- `webapp/ui_from_testpers/src/fishing.css` (`.slot-image` styles)

### 5. ✅ Container Scrolling
**Problem**: No scrolling on fishing screen when content overflows
**Solution**:
- Already present in CSS: `.fishing-container` has `overflow-y: auto`
- Should work on mobile with `-webkit-overflow-scrolling: touch`

**Files**: No changes needed (already implemented)

## Database Migration

The migration script `add_ton_balance_migration.py` is ready but needs to be run on the server.

### Migration Details:
- Adds `ton_balance REAL DEFAULT 0` column to `players` table
- Safe to run multiple times (checks if column exists)
- Auto-detects PostgreSQL vs SQLite
- Required for TON payment functionality

## Testing Checklist

Before deploying, verify locally:

- [ ] Stars invoice opens in-app dialog
- [ ] TON Connect wallet connection works
- [ ] Fish result modal appears with animation
- [ ] Slot animation scrolls smoothly with fish images
- [ ] Detailed fish info shown (name, weight, length, rarity, XP)
- [ ] Container scrolls on mobile

## Known Remaining Issues

1. **Stars payment callback** - Need to test actual payment flow with real bot
2. **TON transaction verification** - Backend should verify blockchain transaction
3. **Inventory integration** - Caught fish should appear in inventory (already in backend)
4. **All game logic events** - Fish inspector, snap, boat crash, treasures, events need frontend display

## Next Steps

1. **Deploy changes** (see DEPLOYMENT_GUIDE.md)
2. **Run migration** on server:
   ```bash
   docker exec -it fishbot_app_1 python add_ton_balance_migration.py
   ```
3. **Test all payment flows** with small amounts
4. **Implement remaining game logic display**:
   - Fish inspector confiscation
   - Snap (fish escapes)
   - Boat crash warnings
   - Treasure notifications
   - Location events (spawn, murder, school)
5. **Add inventory sync** - Show caught fish count
6. **Add level-up animations**

## Files Changed Summary

```
webapp/app.py                                          (+7 lines)
webapp/ui_from_testpers/src/ui/fishingScreen.ts       (~50 lines modified)
webapp/ui_from_testpers/src/modules/telegram.ts       (+2 properties)
webapp/ui_from_testpers/src/fishing.css               (~10 lines modified)
```

## Deployment Commands

```bash
# On server:
cd /opt/bots/fishbot
git pull
docker-compose down
docker-compose up -d --build

# Wait for containers to start, then:
docker exec -it fishbot_app_1 python add_ton_balance_migration.py

# Check logs:
docker-compose logs -f app
```

## Verification After Deploy

1. Open mini-app in Telegram
2. Go to Fishing screen (ИГРЫ → РЫБАЛКА)
3. Test Stars top-up → should open invoice in-app
4. Test TON top-up → should open wallet connector without manifest error
5. Click "ФИШ" button → wait for result → modal should appear
6. Check slot animation → should scroll fish images smoothly
7. Verify fish details in modal → name, weight, rarity, XP

---

## Technical Notes

### Stars Payment Flow:
1. Frontend calls `/api/create-stars-invoice` with amount
2. Backend returns invoice link
3. Frontend calls `tgService.webApp.openInvoice(link, callback)`
4. User pays in Telegram dialog
5. Callback receives status: 'paid', 'cancelled', or 'failed'
6. Frontend updates balance locally and shows confirmation

### TON Payment Flow:
1. Frontend checks if wallet connected via `tonConnectService`
2. If not connected, prompts connection
3. Calls `tonConnectService.sendTransaction(amount, memo)`
4. Transaction sent to blockchain
5. On success, calls `/api/confirm-ton-topup` to update backend balance
6. Frontend updates balance display

### Slot Animation:
- Uses CSS transform `translateY(-50px)` for upward movement
- Opacity fades during transition (0.3 → 1.0)
- Scale effect (0.7 → 1.0) adds depth
- Progressive slowdown simulates real slot machine
- Final result shown with bounce animation (`fishAppear`)

### Fish Result Modal:
- Created dynamically on each catch
- Displays fish image (or trash image)
- Shows detailed stats from backend
- Supports all catch types: fish, trash, no_bite, snap, inspector
- Auto-removed on close with fade-out animation

