# Yamaha Receiver

Home Assistant custom integration for compatible legacy Yamaha receivers that expose the Yamaha Web Control interface.

## Overview

This library exposes a separate media player entity for each zone operated by the receiver.  Each entity can:

1. Be turned on and off
2. Be muted, and have its volume adjusted
3. Select a source from the available list of sources (which should be populated according to the sources actually available on the receiver)
4. (In the case of the main zone) select an audio program

It also exposes a sensor entity which provides some general information about the amplifier.  

## Installation with HACS

1. Open **HACS** in Home Assistant.
2. Select **Integrations**, open the three-dot menu, and choose **Custom repositories**.
3. Add [https://github.com/stemotechtips/legacy_yamaha_receiver_ha](https://github.com/stemotechtips/legacy_yamaha_receiver_ha), select **Integration**, and click **Add**.
4. Search for **Yamaha Receiver** and install it.
5. Restart Home Assistant.
6. Add the integration from **Settings > Devices & services > Add integration**.

Enter the receiver's IP address when prompted. The receiver must be reachable from the Home Assistant host.

## Manual installation

Copy the `custom_components/legacy_yamaha_receiver_ha` directory into the `custom_components` directory of your Home Assistant configuration, then restart Home Assistant.

## Removal

Remove the integration from **Settings > Devices & services**, delete `custom_components/legacy_yamaha_receiver_ha`, and restart Home Assistant.