import UIKit
import StoreKit

class CheckoutViewController: UIViewController {
    override func viewDidLoad() {
        super.viewDidLoad()
        setupStoreKit()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
    }

    override func viewDidDisappear(_ animated: Bool) {
        super.viewDidDisappear(animated)
    }

    func setupStoreKit() async {
        for await result in Transaction.updates {
            print("Transaction updated: \(result)")
        }
    }
}
