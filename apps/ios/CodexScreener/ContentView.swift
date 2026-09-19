import SwiftUI
import WebKit

struct ContentView: View {
    @State private var isLoading = true
    @State private var loadProgress: Double = 0

    var body: some View {
        ZStack {
            Color(red: 0.04, green: 0.04, blue: 0.07)
                .ignoresSafeArea()

            WebView(
                url: URL(string: "https://breakoutscan-web.vercel.app")!,
                isLoading: $isLoading,
                loadProgress: $loadProgress
            )
            .ignoresSafeArea(.container, edges: [.top, .bottom, .leading, .trailing])

            if isLoading {
                LaunchOverlay(progress: loadProgress)
            }
        }
        .preferredColorScheme(.dark)
    }
}

// MARK: - Launch overlay shown while web app loads
struct LaunchOverlay: View {
    let progress: Double

    var body: some View {
        ZStack {
            Color(red: 0.04, green: 0.04, blue: 0.07)
                .ignoresSafeArea()

            VStack(spacing: 24) {
                Spacer()

                // App icon / logo
                ZStack {
                    RoundedRectangle(cornerRadius: 24)
                        .fill(
                            LinearGradient(
                                colors: [
                                    Color(red: 0.55, green: 0.36, blue: 1.0),
                                    Color(red: 0.35, green: 0.20, blue: 0.85)
                                ],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 80, height: 80)
                        .shadow(color: Color.purple.opacity(0.4), radius: 20)

                    Image(systemName: "chart.line.uptrend.xyaxis")
                        .font(.system(size: 36, weight: .bold))
                        .foregroundColor(.white)
                }

                Text("BreakoutScan")
                    .font(.system(size: 28, weight: .bold, design: .rounded))
                    .foregroundColor(.white)

                Text("Real-time Indian Stock Screener")
                    .font(.subheadline)
                    .foregroundColor(.gray)

                Spacer()

                // Progress bar
                VStack(spacing: 8) {
                    ProgressView(value: progress)
                        .progressViewStyle(LinearProgressViewStyle(tint: Color.purple))
                        .frame(width: 200)

                    Text("Loading...")
                        .font(.caption)
                        .foregroundColor(.gray)
                }
                .padding(.bottom, 60)
            }
        }
    }
}

// MARK: - WKWebView wrapper
struct WebView: UIViewRepresentable {
    let url: URL
    @Binding var isLoading: Bool
    @Binding var loadProgress: Double

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []

        // Inject viewport meta tag override to ensure proper scaling
        let script = WKUserScript(
            source: """
            var meta = document.querySelector('meta[name=viewport]');
            if (!meta) {
                meta = document.createElement('meta');
                meta.name = 'viewport';
                document.head.appendChild(meta);
            }
            meta.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
            """,
            injectionTime: .atDocumentEnd,
            forMainFrameOnly: true
        )
        config.userContentController.addUserScript(script)

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.scrollView.contentInsetAdjustmentBehavior = .automatic
        webView.isOpaque = false
        webView.backgroundColor = UIColor(red: 0.04, green: 0.04, blue: 0.07, alpha: 1)
        webView.scrollView.backgroundColor = UIColor(red: 0.04, green: 0.04, blue: 0.07, alpha: 1)

        // Prevent zoom
        webView.scrollView.minimumZoomScale = 1.0
        webView.scrollView.maximumZoomScale = 1.0
        webView.scrollView.bouncesZoom = false

        // Observe loading progress
        webView.addObserver(context.coordinator, forKeyPath: "estimatedProgress", options: .new, context: nil)

        // Enable pull-to-refresh
        let refreshControl = UIRefreshControl()
        refreshControl.tintColor = .systemPurple
        refreshControl.addTarget(context.coordinator, action: #selector(Coordinator.handleRefresh(_:)), for: .valueChanged)
        webView.scrollView.refreshControl = refreshControl

        // Load the app
        webView.load(URLRequest(url: url))

        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {}

    class Coordinator: NSObject, WKNavigationDelegate {
        var parent: WebView

        init(_ parent: WebView) {
            self.parent = parent
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            // Inject CSS for safe areas, scrollbar hiding, and proper fit
            let safeAreaCSS = """
            (function() {
                var style = document.createElement('style');
                style.textContent = `
                    html, body {
                        -webkit-touch-callout: none;
                        overscroll-behavior: none;
                        overflow-x: hidden;
                        max-width: 100vw;
                    }
                    ::-webkit-scrollbar { display: none; }
                    body {
                        min-height: 100vh;
                        min-height: -webkit-fill-available;
                        box-sizing: border-box;
                        padding-top: env(safe-area-inset-top);
                        padding-bottom: env(safe-area-inset-bottom);
                        padding-left: env(safe-area-inset-left);
                        padding-right: env(safe-area-inset-right);
                    }
                    img, video, canvas, svg { max-width: 100%; }
                    table { max-width: 100%; overflow-x: auto; display: block; }
                    button, a, [role="button"] {
                        -webkit-tap-highlight-color: transparent;
                        touch-action: manipulation;
                        min-height: 44px;
                        min-width: 44px;
                    }
                    [class*="dropdown"], [class*="modal"], [class*="popover"] {
                        background-color: var(--bg-card, #1a1f2e) !important;
                    }
                `;
                document.head.appendChild(style);
            })();
            """
            webView.evaluateJavaScript(safeAreaCSS)

            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                withAnimation(.easeOut(duration: 0.3)) {
                    self.parent.isLoading = false
                }
            }
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            parent.isLoading = false
        }

        // Open external links in Safari
        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            if let url = navigationAction.request.url {
                let host = url.host ?? ""
                if navigationAction.navigationType == .linkActivated &&
                   !host.contains("breakoutscan-web.vercel.app") &&
                   !host.contains(".vercel.app") &&
                   !host.contains("gruaokvbcnvgvklhqimw.supabase.co") &&
                   !host.contains("localhost") {
                    UIApplication.shared.open(url)
                    decisionHandler(.cancel)
                    return
                }
            }
            decisionHandler(.allow)
        }

        override func observeValue(forKeyPath keyPath: String?, of object: Any?, change: [NSKeyValueChangeKey: Any]?, context: UnsafeMutableRawPointer?) {
            if keyPath == "estimatedProgress", let webView = object as? WKWebView {
                DispatchQueue.main.async {
                    self.parent.loadProgress = webView.estimatedProgress
                }
            }
        }

        @objc func handleRefresh(_ sender: UIRefreshControl) {
            if let webView = sender.superview?.superview as? WKWebView {
                webView.reload()
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
                sender.endRefreshing()
            }
        }
    }
}

#Preview {
    ContentView()
}
