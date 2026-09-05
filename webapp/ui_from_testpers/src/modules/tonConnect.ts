// ─────────────────────────────────────────────────────────────────────────────
// TON Connect integration
// ─────────────────────────────────────────────────────────────────────────────
import { TonConnectUI, Wallet } from '@tonconnect/ui';

const MANIFEST_URL = 'https://fish.monkeysdynasty.website/tonconnect-manifest.json';
const RECIPIENT_WALLET = 'UQBVTCudYNrI11UXM04V6Lq9KWc2HurxVr2BtkMeZfmyBvuC'; // tensazangetsu.ton (bounceable format)

class TonConnectService {
  private tonConnectUI: TonConnectUI | null = null;
  private wallet: Wallet | null = null;

  async init(): Promise<void> {
    if (this.tonConnectUI) return;

    try {
      this.tonConnectUI = new TonConnectUI({
        manifestUrl: MANIFEST_URL,
        buttonRootId: null
      });

      // Subscribe to wallet changes
      this.tonConnectUI.onStatusChange((wallet) => {
        this.wallet = wallet;
        console.log('TON Wallet status changed:', wallet);
      });

      // Check if already connected
      const currentWallet = this.tonConnectUI.wallet;
      if (currentWallet) {
        this.wallet = currentWallet;
      }
    } catch (error) {
      console.error('Failed to initialize TON Connect:', error);
    }
  }

  async connect(): Promise<boolean> {
    if (!this.tonConnectUI) {
      await this.init();
    }

    try {
      if (this.tonConnectUI && !this.wallet) {
        await this.tonConnectUI.openModal();
        // Wait for connection
        return new Promise((resolve) => {
          const unsubscribe = this.tonConnectUI!.onStatusChange((wallet) => {
            if (wallet) {
              this.wallet = wallet;
              unsubscribe();
              resolve(true);
            }
          });
          
          // Timeout after 60 seconds
          setTimeout(() => {
            unsubscribe();
            resolve(false);
          }, 60000);
        });
      }
      return !!this.wallet;
    } catch (error) {
      console.error('Failed to connect wallet:', error);
      return false;
    }
  }

  async disconnect(): Promise<void> {
    if (this.tonConnectUI) {
      await this.tonConnectUI.disconnect();
      this.wallet = null;
    }
  }

  isConnected(): boolean {
    return !!this.wallet;
  }

  getWalletAddress(): string | null {
    return this.wallet?.account?.address || null;
  }

  /**
   * Send TON transaction
   * @param amountTON Amount in TON (e.g., 0.01 for 0.01 TON)
   * @param comment Optional comment for the transaction
   */
  async sendTransaction(amountTON: number, comment?: string): Promise<{ success: boolean; error?: string }> {
    if (!this.tonConnectUI) {
      await this.init();
    }

    if (!this.wallet) {
      const connected = await this.connect();
      if (!connected) {
        return { success: false, error: 'Wallet not connected' };
      }
    }

    try {
      // Convert TON to nanoTON (1 TON = 1,000,000,000 nanoTON)
      const amountNano = Math.floor(amountTON * 1_000_000_000).toString();

      const transaction = {
        validUntil: Math.floor(Date.now() / 1000) + 300, // 5 minutes
        messages: [
          {
            address: RECIPIENT_WALLET,
            amount: amountNano,
            payload: comment ? this.createCommentPayload(comment) : undefined
          }
        ]
      };

      console.log('Sending transaction:', transaction);
      const result = await this.tonConnectUI!.sendTransaction(transaction);
      console.log('Transaction result:', result);

      return { success: true };
    } catch (error: any) {
      console.error('Transaction failed:', error);
      return { 
        success: false, 
        error: error?.message || 'Transaction failed' 
      };
    }
  }

  /**
   * Create comment payload for transaction
   */
  private createCommentPayload(comment: string): string {
    // Simple text comment (начинается с 0x00000000 в hex)
    const bytes = new TextEncoder().encode(comment);
    const hex = Array.from(bytes)
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
    return '0x00000000' + hex;
  }

  /**
   * Top up balance with TON
   * @param amountTON Amount in TON to send
   * @param userId User ID for tracking
   */
  async topUpWithTON(amountTON: number, userId: number): Promise<{ success: boolean; error?: string }> {
    const comment = `TopUp:${userId}:${Date.now()}`;
    return await this.sendTransaction(amountTON, comment);
  }
}

export const tonConnectService = new TonConnectService();
