import SwiftUI

struct CheckoutView: View {
    @State var totalAmount: Double = 99.99
    @Binding var isPresented: Bool

    var body: some View {
        VStack {
            Text("Total: \(totalAmount)")
            Button("Dismiss") {
                isPresented = false
            }
        }
    }
}
