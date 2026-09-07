package dev.agenttools.javacodemap;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.eclipse.jdt.core.JavaCore;
import org.eclipse.jdt.core.compiler.IProblem;
import org.eclipse.jdt.core.dom.AST;
import org.eclipse.jdt.core.dom.ASTNode;
import org.eclipse.jdt.core.dom.ASTParser;
import org.eclipse.jdt.core.dom.ASTVisitor;
import org.eclipse.jdt.core.dom.AbstractTypeDeclaration;
import org.eclipse.jdt.core.dom.AnnotationTypeDeclaration;
import org.eclipse.jdt.core.dom.AnnotationTypeMemberDeclaration;
import org.eclipse.jdt.core.dom.BodyDeclaration;
import org.eclipse.jdt.core.dom.ClassInstanceCreation;
import org.eclipse.jdt.core.dom.CompilationUnit;
import org.eclipse.jdt.core.dom.EnumConstantDeclaration;
import org.eclipse.jdt.core.dom.EnumDeclaration;
import org.eclipse.jdt.core.dom.FieldDeclaration;
import org.eclipse.jdt.core.dom.IBinding;
import org.eclipse.jdt.core.dom.IMethodBinding;
import org.eclipse.jdt.core.dom.ITypeBinding;
import org.eclipse.jdt.core.dom.IVariableBinding;
import org.eclipse.jdt.core.dom.MethodInvocation;
import org.eclipse.jdt.core.dom.MethodDeclaration;
import org.eclipse.jdt.core.dom.SimpleName;
import org.eclipse.jdt.core.dom.SuperMethodInvocation;
import org.eclipse.jdt.core.dom.TypeDeclaration;
import org.eclipse.jdt.core.dom.VariableDeclarationFragment;

public final class JdtAstHelper {
    private JdtAstHelper() {
    }

    public static void main(String[] args) throws Exception {
        Request request = Request.parse(args);
        if (!"map".equals(request.command)) {
            throw new IllegalArgumentException("unsupported command: " + request.command);
        }
        String source = Files.readString(request.file, StandardCharsets.UTF_8);
        CompilationUnit unit = parse(request, source);
        Map<String, Object> payload = new HashMap<>();
        payload.put("file", request.file.toString());
        payload.put("schema_version", 1);
        payload.put("engine", "jdt");
        payload.put("ast_backend", "jdt");
        payload.put("semantic", true);
        payload.put("confidence", "jdt-ast");
        List<Map<String, Object>> symbols = collectSymbols(unit, source);
        List<Map<String, Object>> calls = collectCalls(unit, source, symbols);
        payload.put("diagnostics", problems(unit));
        payload.put("symbols", symbols);
        payload.put("references", collectReferences(unit, source, symbols));
        payload.put("calls", calls);
        payload.put("call_graph", collectCallGraph(calls));
        System.out.println(Json.write(payload));
    }

    @SuppressWarnings("deprecation")
    private static CompilationUnit parse(Request request, String source) {
        ASTParser parser = ASTParser.newParser(AST.JLS21);
        parser.setKind(ASTParser.K_COMPILATION_UNIT);
        parser.setSource(source.toCharArray());
        parser.setUnitName(request.file.getFileName().toString());
        parser.setResolveBindings(true);
        parser.setBindingsRecovery(true);
        parser.setStatementsRecovery(true);
        parser.setCompilerOptions(JavaCore.getOptions());
        String[] classpath = request.classpath.stream().map(Path::toString).toArray(String[]::new);
        String[] sourcepath = request.sourcepath.stream().map(Path::toString).toArray(String[]::new);
        String[] encodings = new String[sourcepath.length];
        for (int index = 0; index < encodings.length; index++) {
            encodings[index] = StandardCharsets.UTF_8.name();
        }
        parser.setEnvironment(classpath, sourcepath, encodings, true);
        return (CompilationUnit) parser.createAST(null);
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> collectSymbols(CompilationUnit unit, String source) {
        List<Map<String, Object>> result = new ArrayList<>();
        for (Object typeObject : unit.types()) {
            if (typeObject instanceof AbstractTypeDeclaration typeDeclaration) {
                result.add(typeSymbol(unit, source, typeDeclaration, List.of()));
            }
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> typeSymbol(
            CompilationUnit unit,
            String source,
            AbstractTypeDeclaration declaration,
            List<String> parents) {
        String name = declaration.getName().getIdentifier();
        List<String> qualifiedParts = new ArrayList<>(parents);
        qualifiedParts.add(name);
        ITypeBinding binding = null;
        if (declaration instanceof TypeDeclaration typeDeclaration) {
            binding = typeDeclaration.resolveBinding();
        } else if (declaration instanceof EnumDeclaration enumDeclaration) {
            binding = enumDeclaration.resolveBinding();
        } else if (declaration instanceof AnnotationTypeDeclaration annotationTypeDeclaration) {
            binding = annotationTypeDeclaration.resolveBinding();
        }
        String qualifiedName = binding != null && !binding.getQualifiedName().isBlank()
                ? binding.getQualifiedName()
                : String.join(".", qualifiedParts);
        Map<String, Object> payload = symbolPayload(unit, source, declaration, name, qualifiedName, typeKind(declaration), null);
        List<Map<String, Object>> children = new ArrayList<>();
        for (Object bodyObject : declaration.bodyDeclarations()) {
            if (bodyObject instanceof BodyDeclaration bodyDeclaration) {
                children.addAll(bodySymbols(unit, source, bodyDeclaration, qualifiedName));
            }
        }
        if (declaration instanceof EnumDeclaration enumDeclaration) {
            for (Object constantObject : enumDeclaration.enumConstants()) {
                if (constantObject instanceof EnumConstantDeclaration constant) {
                    String childName = constant.getName().getIdentifier();
                    children.add(symbolPayload(unit, source, constant, childName, qualifiedName + "." + childName, "enum_value", null));
                }
            }
        }
        payload.put("children", children);
        return payload;
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> bodySymbols(
            CompilationUnit unit,
            String source,
            BodyDeclaration declaration,
            String parentName) {
        List<Map<String, Object>> result = new ArrayList<>();
        if (declaration instanceof MethodDeclaration method) {
            String name = method.getName().getIdentifier();
            IMethodBinding binding = method.resolveBinding();
            String qualifiedName = binding != null ? methodBindingName(binding) : parentName + "." + name;
            result.add(symbolPayload(unit, source, method, name, qualifiedName,
                    method.isConstructor() ? "constructor" : "method", method.getBody()));
        } else if (declaration instanceof FieldDeclaration field) {
            for (Object fragmentObject : field.fragments()) {
                if (fragmentObject instanceof VariableDeclarationFragment fragment) {
                    IVariableBinding binding = fragment.resolveBinding();
                    String name = fragment.getName().getIdentifier();
                    String qualifiedName = binding != null ? binding.getVariableDeclaration().getName() : parentName + "." + name;
                    result.add(symbolPayload(unit, source, field, name, qualifiedName, "field", null));
                }
            }
        } else if (declaration instanceof AbstractTypeDeclaration nestedType) {
            result.add(typeSymbol(unit, source, nestedType, List.of(parentName)));
        } else if (declaration instanceof AnnotationTypeMemberDeclaration member) {
            String name = member.getName().getIdentifier();
            result.add(symbolPayload(unit, source, member, name, parentName + "." + name, "annotation_member", null));
        }
        return result;
    }

    private static String typeKind(AbstractTypeDeclaration declaration) {
        if (declaration instanceof TypeDeclaration typeDeclaration) {
            return typeDeclaration.isInterface() ? "interface" : "class";
        }
        if (declaration instanceof EnumDeclaration) {
            return "enum";
        }
        if (declaration instanceof AnnotationTypeDeclaration) {
            return "annotation_type";
        }
        return "type";
    }

    private static String methodBindingName(IMethodBinding binding) {
        IMethodBinding declaration = binding.getMethodDeclaration();
        ITypeBinding declaringClass = declaration.getDeclaringClass();
        String owner = declaringClass == null ? "" : declaringClass.getQualifiedName();
        return owner.isBlank() ? declaration.getName() : owner + "." + declaration.getName();
    }

    private static List<Map<String, Object>> collectReferences(
            CompilationUnit unit,
            String source,
            List<Map<String, Object>> symbols) {
        List<Map<String, Object>> result = new ArrayList<>();
        unit.accept(new ASTVisitor() {
            @Override
            public boolean visit(SimpleName node) {
                if (isDeclarationName(node)) {
                    return true;
                }
                IBinding binding = node.resolveBinding();
                SourceSpan span = span(unit, node);
                Map<String, Object> payload = new HashMap<>();
                payload.put("name", node.getIdentifier());
                payload.put("qualified_name", bindingQualifiedName(binding));
                payload.put("binding_key", binding == null ? "" : binding.getKey());
                payload.put("binding_kind", bindingKind(binding));
                payload.put("kind", referenceKind(node));
                payload.put("line", span.startLine);
                payload.put("column", span.startColumn);
                payload.put("span", span.toJson());
                payload.put("text", source.substring(span.startOffset, span.endOffset));
                payload.put("enclosing_symbol", enclosingSymbolName(span.startOffset, symbols));
                result.add(payload);
                return true;
            }
        });
        return result;
    }

    private static List<Map<String, Object>> collectCalls(
            CompilationUnit unit,
            String source,
            List<Map<String, Object>> symbols) {
        List<Map<String, Object>> result = new ArrayList<>();
        unit.accept(new ASTVisitor() {
            @Override
            public boolean visit(MethodInvocation node) {
                result.add(callPayload(unit, source, node.getName(), node.resolveMethodBinding(), symbols, "method_invocation"));
                return true;
            }

            @Override
            public boolean visit(SuperMethodInvocation node) {
                result.add(callPayload(unit, source, node.getName(), node.resolveMethodBinding(), symbols, "super_method_invocation"));
                return true;
            }

            @Override
            public boolean visit(ClassInstanceCreation node) {
                IMethodBinding binding = node.resolveConstructorBinding();
                result.add(callPayload(unit, source, node, binding, symbols, "constructor_invocation"));
                return true;
            }
        });
        return result;
    }

    private static List<Map<String, Object>> collectCallGraph(List<Map<String, Object>> calls) {
        List<Map<String, Object>> result = new ArrayList<>();
        for (Map<String, Object> call : calls) {
            String from = String.valueOf(call.getOrDefault("enclosing_symbol", ""));
            if (from.isBlank()) {
                continue;
            }
            Map<String, Object> edge = new HashMap<>();
            edge.put("from", from);
            edge.put("to", String.valueOf(call.getOrDefault("qualified_name", call.getOrDefault("name", ""))));
            edge.put("name", String.valueOf(call.getOrDefault("name", "")));
            edge.put("line", call.get("line"));
            edge.put("column", call.get("column"));
            edge.put("binding_key", String.valueOf(call.getOrDefault("binding_key", "")));
            result.add(edge);
        }
        return result;
    }

    private static Map<String, Object> callPayload(
            CompilationUnit unit,
            String source,
            ASTNode nameNode,
            IMethodBinding binding,
            List<Map<String, Object>> symbols,
            String kind) {
        SourceSpan span = span(unit, nameNode);
        Map<String, Object> payload = new HashMap<>();
        payload.put("name", binding == null ? source.substring(span.startOffset, span.endOffset) : binding.getName());
        payload.put("qualified_name", binding == null ? "" : methodBindingName(binding));
        payload.put("binding_key", binding == null ? "" : binding.getMethodDeclaration().getKey());
        payload.put("kind", kind);
        payload.put("line", span.startLine);
        payload.put("column", span.startColumn);
        payload.put("span", span.toJson());
        payload.put("text", source.substring(span.startOffset, span.endOffset));
        payload.put("enclosing_symbol", enclosingSymbolName(span.startOffset, symbols));
        return payload;
    }

    private static boolean isDeclarationName(SimpleName node) {
        ASTNode parent = node.getParent();
        if (parent instanceof TypeDeclaration typeDeclaration && typeDeclaration.getName() == node) {
            return true;
        }
        if (parent instanceof EnumDeclaration enumDeclaration && enumDeclaration.getName() == node) {
            return true;
        }
        if (parent instanceof AnnotationTypeDeclaration annotationDeclaration && annotationDeclaration.getName() == node) {
            return true;
        }
        if (parent instanceof MethodDeclaration methodDeclaration && methodDeclaration.getName() == node) {
            return true;
        }
        if (parent instanceof VariableDeclarationFragment fragment && fragment.getName() == node) {
            return true;
        }
        if (parent instanceof EnumConstantDeclaration constant && constant.getName() == node) {
            return true;
        }
        if (parent instanceof AnnotationTypeMemberDeclaration member && member.getName() == node) {
            return true;
        }
        return false;
    }

    private static String bindingQualifiedName(IBinding binding) {
        if (binding instanceof ITypeBinding typeBinding) {
            return typeBinding.getTypeDeclaration().getQualifiedName();
        }
        if (binding instanceof IMethodBinding methodBinding) {
            return methodBindingName(methodBinding);
        }
        if (binding instanceof IVariableBinding variableBinding) {
            IVariableBinding declaration = variableBinding.getVariableDeclaration();
            ITypeBinding owner = declaration.getDeclaringClass();
            if (owner != null && !owner.getQualifiedName().isBlank()) {
                return owner.getQualifiedName() + "." + declaration.getName();
            }
            return declaration.getName();
        }
        return "";
    }

    private static String bindingKind(IBinding binding) {
        if (binding instanceof ITypeBinding) {
            return "type";
        }
        if (binding instanceof IMethodBinding) {
            return "method";
        }
        if (binding instanceof IVariableBinding variableBinding) {
            if (variableBinding.isField()) {
                return "field";
            }
            if (variableBinding.isParameter()) {
                return "parameter";
            }
            return "variable";
        }
        return "";
    }

    private static String referenceKind(SimpleName node) {
        ASTNode parent = node.getParent();
        if (parent instanceof MethodInvocation methodInvocation && methodInvocation.getName() == node) {
            return "call";
        }
        if (parent instanceof SuperMethodInvocation superMethodInvocation && superMethodInvocation.getName() == node) {
            return "call";
        }
        return "reference";
    }

    private static String enclosingSymbolName(int offset, List<Map<String, Object>> symbols) {
        Map<String, Object> best = enclosingSymbol(offset, symbols, null);
        return best == null ? "" : String.valueOf(best.getOrDefault("qualified_name", ""));
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> enclosingSymbol(
            int offset,
            List<Map<String, Object>> symbols,
            Map<String, Object> best) {
        for (Map<String, Object> symbol : symbols) {
            Object spanObject = symbol.get("span");
            if (spanObject instanceof Map<?, ?> span
                    && containsOffset(span, offset)
                    && (best == null || spanStart(span) >= spanStart((Map<?, ?>) best.get("span")))) {
                best = symbol;
            }
            Object childrenObject = symbol.get("children");
            if (childrenObject instanceof List<?> children) {
                best = enclosingSymbol(offset, (List<Map<String, Object>>) children, best);
            }
        }
        return best;
    }

    private static boolean containsOffset(Map<?, ?> span, int offset) {
        return spanStart(span) <= offset && offset <= spanEnd(span);
    }

    private static int spanStart(Map<?, ?> span) {
        Object value = span.get("start_offset");
        return value instanceof Number number ? number.intValue() : -1;
    }

    private static int spanEnd(Map<?, ?> span) {
        Object value = span.get("end_offset");
        return value instanceof Number number ? number.intValue() : -1;
    }

    private static Map<String, Object> symbolPayload(
            CompilationUnit unit,
            String source,
            ASTNode node,
            String name,
            String qualifiedName,
            String kind,
            ASTNode bodyNode) {
        SourceSpan span = span(unit, node);
        SourceSpan bodySpan = bodyNode == null ? null : innerBodySpan(unit, bodyNode);
        Map<String, Object> payload = new HashMap<>();
        payload.put("name", name);
        payload.put("qualified_name", qualifiedName);
        payload.put("kind", kind);
        payload.put("span", span.toJson());
        payload.put("body_span", bodySpan == null ? null : bodySpan.toJson());
        payload.put("hash", sha256(source.substring(span.startOffset, span.endOffset)));
        payload.put("body_hash", bodySpan == null ? null : sha256(source.substring(bodySpan.startOffset, bodySpan.endOffset)));
        payload.put("children", List.of());
        return payload;
    }

    private static SourceSpan span(CompilationUnit unit, ASTNode node) {
        int start = node.getStartPosition();
        int end = start + node.getLength();
        return new SourceSpan(
                unit.getLineNumber(start),
                unit.getColumnNumber(start) + 1,
                unit.getLineNumber(Math.max(start, end - 1)),
                unit.getColumnNumber(Math.max(start, end - 1)) + 2,
                start,
                end);
    }

    private static SourceSpan innerBodySpan(CompilationUnit unit, ASTNode bodyNode) {
        int start = bodyNode.getStartPosition();
        int end = start + bodyNode.getLength();
        return new SourceSpan(
                unit.getLineNumber(start + 1),
                unit.getColumnNumber(start + 1) + 1,
                unit.getLineNumber(Math.max(start + 1, end - 2)),
                unit.getColumnNumber(Math.max(start + 1, end - 2)) + 2,
                start + 1,
                end - 1);
    }

    private static List<Map<String, Object>> problems(CompilationUnit unit) {
        List<Map<String, Object>> result = new ArrayList<>();
        for (IProblem problem : unit.getProblems()) {
            Map<String, Object> payload = new HashMap<>();
            payload.put("message", problem.getMessage());
            payload.put("line", problem.getSourceLineNumber());
            payload.put("severity", problem.isError() ? "error" : "warning");
            result.add(payload);
        }
        return result;
    }

    private static String sha256(String text) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] encoded = digest.digest(text.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder();
            for (byte value : encoded) {
                builder.append(String.format("%02x", value));
            }
            return builder.toString();
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException(error);
        }
    }

    private record SourceSpan(
            int startLine,
            int startColumn,
            int endLine,
            int endColumn,
            int startOffset,
            int endOffset) {
        Map<String, Object> toJson() {
            Map<String, Object> payload = new HashMap<>();
            payload.put("start_line", startLine);
            payload.put("start_column", startColumn);
            payload.put("end_line", endLine);
            payload.put("end_column", endColumn);
            payload.put("start_offset", startOffset);
            payload.put("end_offset", endOffset);
            return payload;
        }
    }

    private static final class Request {
        final String command;
        final Path file;
        final List<Path> classpath;
        final List<Path> sourcepath;

        private Request(String command, Path file, List<Path> classpath, List<Path> sourcepath) {
            this.command = command;
            this.file = file;
            this.classpath = classpath;
            this.sourcepath = sourcepath;
        }

        static Request parse(String[] args) throws IOException {
            String command = args.length == 0 ? "" : args[0];
            Path file = null;
            List<Path> classpath = new ArrayList<>();
            List<Path> sourcepath = new ArrayList<>();
            for (int index = 1; index < args.length; index++) {
                String arg = args[index];
                if ("--file".equals(arg)) {
                    file = Path.of(requireValue(args, ++index, arg)).toAbsolutePath().normalize();
                } else if ("--classpath".equals(arg)) {
                    classpath.add(Path.of(requireValue(args, ++index, arg)).toAbsolutePath().normalize());
                } else if ("--sourcepath".equals(arg)) {
                    sourcepath.add(Path.of(requireValue(args, ++index, arg)).toAbsolutePath().normalize());
                } else if ("--release".equals(arg)) {
                    index++;
                } else {
                    throw new IllegalArgumentException("unknown argument: " + arg);
                }
            }
            if (file == null) {
                throw new IllegalArgumentException("--file is required");
            }
            return new Request(command, file, classpath, sourcepath);
        }

        private static String requireValue(String[] args, int index, String option) {
            if (index >= args.length) {
                throw new IllegalArgumentException(option + " requires a value");
            }
            return args[index];
        }
    }

    private static final class Json {
        private Json() {
        }

        static String write(Object value) {
            if (value == null) {
                return "null";
            }
            if (value instanceof String text) {
                return quote(text);
            }
            if (value instanceof Number || value instanceof Boolean) {
                return value.toString();
            }
            if (value instanceof Map<?, ?> map) {
                List<String> parts = new ArrayList<>();
                for (Map.Entry<?, ?> entry : map.entrySet()) {
                    parts.add(quote(String.valueOf(entry.getKey())) + ":" + write(entry.getValue()));
                }
                return "{" + String.join(",", parts) + "}";
            }
            if (value instanceof Iterable<?> iterable) {
                List<String> parts = new ArrayList<>();
                for (Object item : iterable) {
                    parts.add(write(item));
                }
                return "[" + String.join(",", parts) + "]";
            }
            return quote(String.valueOf(value));
        }

        private static String quote(String text) {
            StringBuilder builder = new StringBuilder("\"");
            for (int index = 0; index < text.length(); index++) {
                char value = text.charAt(index);
                switch (value) {
                    case '\\' -> builder.append("\\\\");
                    case '"' -> builder.append("\\\"");
                    case '\n' -> builder.append("\\n");
                    case '\r' -> builder.append("\\r");
                    case '\t' -> builder.append("\\t");
                    default -> {
                        if (value < 0x20) {
                            builder.append(String.format("\\u%04x", (int) value));
                        } else {
                            builder.append(value);
                        }
                    }
                }
            }
            return builder.append('"').toString();
        }
    }
}
