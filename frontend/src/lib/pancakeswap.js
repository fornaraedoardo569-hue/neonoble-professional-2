/**
 * PancakeSwap V2 on-chain swap (BSC mainnet).
 *
 * Strict design constraints:
 *  - Non-custodial: every transaction is signed by the user's connected
 *    wallet via window.ethereum. NeoNoble never holds private keys.
 *  - Read-only price quotes come from the public PancakeSwap router.
 *  - We use ethers v6 BrowserProvider, talking to the user's wallet.
 *  - All errors are caught and surfaced to the UI — no silent failures.
 */
import { BrowserProvider, Contract, parseUnits, formatUnits, MaxUint256 } from 'ethers';

// PancakeSwap V2 Router on BSC mainnet (canonical address)
export const PANCAKE_V2_ROUTER = '0x10ED43C718714eb63d5aA57B78B54704E256024E';

// USDC on BSC (BEP-20). 18 decimals.
export const BSC_USDC = {
  address: '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',
  symbol: 'USDC',
  decimals: 18,
};

// Minimal ABIs
const ROUTER_ABI = [
  'function getAmountsOut(uint amountIn, address[] calldata path) external view returns (uint[] memory amounts)',
  'function swapExactTokensForTokens(uint amountIn, uint amountOutMin, address[] calldata path, address to, uint deadline) external returns (uint[] memory amounts)',
];

const ERC20_ABI = [
  'function decimals() view returns (uint8)',
  'function symbol() view returns (string)',
  'function balanceOf(address) view returns (uint256)',
  'function allowance(address owner, address spender) view returns (uint256)',
  'function approve(address spender, uint256 amount) returns (bool)',
];

const BSC_HEX_CHAIN_ID = '0x38';

const ensureBSC = async (provider) => {
  const network = await provider.getNetwork();
  const chainHex = '0x' + network.chainId.toString(16);
  if (chainHex !== BSC_HEX_CHAIN_ID) {
    throw new Error(
      `Switch your wallet to BNB Smart Chain (current chainId: ${chainHex}).`
    );
  }
};

export async function getTokenInfo(tokenAddress, provider) {
  const c = new Contract(tokenAddress, ERC20_ABI, provider);
  const [decimals, symbol] = await Promise.all([c.decimals(), c.symbol()]);
  return { address: tokenAddress, symbol, decimals: Number(decimals) };
}

/**
 * Get a price quote: how many `toToken` you get for `amountIn` of `fromToken`.
 * Returns { amountOutRaw: bigint, amountOutHuman: string, route: address[] }
 * Throws if the pool does not exist or has no liquidity.
 */
export async function getSwapQuote({
  amountInHuman,
  fromToken,
  toToken,
}) {
  if (!window.ethereum) throw new Error('No injected wallet');
  const provider = new BrowserProvider(window.ethereum);
  await ensureBSC(provider);
  const router = new Contract(PANCAKE_V2_ROUTER, ROUTER_ABI, provider);
  const amountIn = parseUnits(String(amountInHuman || '0'), fromToken.decimals);
  if (amountIn === 0n) return { amountOutRaw: 0n, amountOutHuman: '0', route: [fromToken.address, toToken.address] };
  const path = [fromToken.address, toToken.address];
  try {
    const amounts = await router.getAmountsOut(amountIn, path);
    const amountOutRaw = amounts[amounts.length - 1];
    return {
      amountOutRaw,
      amountOutHuman: formatUnits(amountOutRaw, toToken.decimals),
      route: path,
    };
  } catch (err) {
    throw new Error(
      'No liquidity pool found for this pair on PancakeSwap. Provide liquidity first or use a routed pair (e.g. via WBNB).'
    );
  }
}

/**
 * Execute the swap.
 *  1. If allowance < amountIn → request approve(MaxUint256)
 *  2. Call swapExactTokensForTokens with slippage tolerance applied
 *
 * Returns the final tx hash.
 */
export async function executeSwap({
  amountInHuman,
  fromToken,
  toToken,
  slippageBps = 100, // 1.00%
  deadlineSeconds = 600,
  onProgress = () => {},
}) {
  if (!window.ethereum) throw new Error('No injected wallet');
  const provider = new BrowserProvider(window.ethereum);
  await ensureBSC(provider);
  const signer = await provider.getSigner();
  const userAddress = await signer.getAddress();

  const router = new Contract(PANCAKE_V2_ROUTER, ROUTER_ABI, signer);
  const erc20 = new Contract(fromToken.address, ERC20_ABI, signer);
  const amountIn = parseUnits(String(amountInHuman), fromToken.decimals);

  // Balance check (fail fast)
  const balance = await erc20.balanceOf(userAddress);
  if (balance < amountIn) {
    throw new Error(
      `Insufficient ${fromToken.symbol} balance. You have ${formatUnits(
        balance,
        fromToken.decimals
      )} but tried to swap ${amountInHuman}.`
    );
  }

  // Quote + slippage minimum
  const quote = await getSwapQuote({ amountInHuman, fromToken, toToken });
  const minOut =
    (quote.amountOutRaw * BigInt(10000 - slippageBps)) / 10000n;

  // Allowance
  onProgress({ step: 'allowance' });
  const allowance = await erc20.allowance(userAddress, PANCAKE_V2_ROUTER);
  if (allowance < amountIn) {
    onProgress({ step: 'approving' });
    const approveTx = await erc20.approve(PANCAKE_V2_ROUTER, MaxUint256);
    onProgress({ step: 'approve_sent', hash: approveTx.hash });
    await approveTx.wait();
    onProgress({ step: 'approved' });
  }

  // Swap
  onProgress({ step: 'swapping' });
  const deadline = Math.floor(Date.now() / 1000) + deadlineSeconds;
  const tx = await router.swapExactTokensForTokens(
    amountIn,
    minOut,
    quote.route,
    userAddress,
    deadline
  );
  onProgress({ step: 'swap_sent', hash: tx.hash });
  await tx.wait();
  onProgress({ step: 'done', hash: tx.hash });
  return tx.hash;
}
