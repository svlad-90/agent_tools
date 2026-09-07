plugins {
    application
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
}

dependencies {
    implementation("org.eclipse.jdt:org.eclipse.jdt.core:3.46.0")
}

application {
    mainClass.set("dev.agenttools.javacodemap.JdtAstHelper")
}

tasks.jar {
    archiveFileName.set("java-code-map-jdt-backend.jar")
    manifest {
        attributes["Main-Class"] = application.mainClass.get()
    }
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
    exclude("META-INF/*.DSA", "META-INF/*.RSA", "META-INF/*.SF")
    from({
        configurations.runtimeClasspath.get().filter { it.isFile }.map { zipTree(it) }
    })
}
