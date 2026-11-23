package com.example.checkout

import android.app.Activity
import android.os.Bundle
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingFlowParams

class CheckoutActivity : Activity() {
    private lateinit var billingClient: BillingClient

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        initBilling()
    }

    override fun onResume() {
        super.onResume()
    }

    override fun onDestroy() {
        super.onDestroy()
    }

    private fun initBilling() {
        billingClient = BillingClient.newBuilder(this).build()
    }

    fun startPurchaseFlow() {
        val params = BillingFlowParams.newBuilder().build()
        billingClient.launchBillingFlow(this, params)
    }
}
