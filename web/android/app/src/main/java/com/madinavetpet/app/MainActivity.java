package com.madinavetpet.app;

import android.os.Bundle;
import android.os.Message;
import android.webkit.CookieManager;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.BridgeWebChromeClient;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        WebView webView = getBridge().getWebView();

        // Razorpay's checkout runs in a third-party iframe and relies on
        // cookies to track a payment attempt across a bank/UPI redirect.
        // Android's WebView, unlike a normal mobile browser, blocks
        // third-party cookies unless explicitly enabled here — without
        // this, non-card payment methods (netbanking, UPI, wallets) can
        // fail silently inside the app while working fine in a browser.
        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);
        cookieManager.setAcceptThirdPartyCookies(webView, true);

        // Netbanking/UPI/3D-Secure hand-offs often call window.open() to
        // move to the bank's own page. Android's WebView drops that
        // silently unless a window handler is implemented — this loads the
        // target URL in the same WebView instead of a real new window, so
        // the redirect actually completes rather than going nowhere.
        webView.getSettings().setSupportMultipleWindows(true);
        webView.getSettings().setJavaScriptCanOpenWindowsAutomatically(true);
        webView.setWebChromeClient(new BridgeWebChromeClient(getBridge()) {
            @Override
            public boolean onCreateWindow(WebView view, boolean isDialog, boolean isUserGesture, Message resultMsg) {
                WebView popup = new WebView(view.getContext());
                popup.setWebViewClient(new WebViewClient() {
                    @Override
                    public boolean shouldOverrideUrlLoading(WebView v, String url) {
                        view.loadUrl(url);
                        return true;
                    }
                });
                WebView.WebViewTransport transport = (WebView.WebViewTransport) resultMsg.obj;
                transport.setWebView(popup);
                resultMsg.sendToTarget();
                return true;
            }
        });
    }
}
