SUMMARY = "Xen runtime harness DomU console collector for Linux Dom0"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

inherit systemd

SRC_URI = " \
    file://collect-consoles.sh \
    file://xen-harness-console.default \
    file://xen-harness-console.service \
"

S = "${WORKDIR}"

RDEPENDS:${PN} += "xen-tools-console xen-tools-xl"

SYSTEMD_SERVICE:${PN} = "xen-harness-console.service"
SYSTEMD_AUTO_ENABLE:${PN} ?= "enable"

do_install() {
    install -d ${D}${libexecdir}/xen-harness
    install -m 0755 ${WORKDIR}/collect-consoles.sh \
        ${D}${libexecdir}/xen-harness/collect-consoles.sh

    install -d ${D}${sysconfdir}/default
    install -m 0644 ${WORKDIR}/xen-harness-console.default \
        ${D}${sysconfdir}/default/xen-harness-console

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/xen-harness-console.service \
        ${D}${systemd_system_unitdir}/xen-harness-console.service
}

FILES:${PN} = " \
    ${libexecdir}/xen-harness/collect-consoles.sh \
    ${sysconfdir}/default/xen-harness-console \
    ${systemd_system_unitdir}/xen-harness-console.service \
"
